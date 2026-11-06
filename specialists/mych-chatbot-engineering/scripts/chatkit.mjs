// Provider-neutral conversation engine for JavaScript (Node.js 18+ or browsers with fetch).
// Mirrors chatkit.py: Tool (validated arguments), Agent (tool loop with a step limit),
// ScriptedModel (deterministic double), adapters for the openai-chat, anthropic-messages
// and gemini request styles, and SlidingWindowMemory. No dependencies.
// The adapters follow documented request and response shapes; in the MYCH-HORIZON
// repository they are tested against local stubs only.

const TYPE_CHECKS = {
  string: (v) => typeof v === 'string',
  boolean: (v) => typeof v === 'boolean',
  integer: (v) => Number.isInteger(v),
  number: (v) => typeof v === 'number' && Number.isFinite(v),
  array: (v) => Array.isArray(v),
  object: (v) => v !== null && typeof v === 'object' && !Array.isArray(v),
};
const KEY_PATTERN = /(sk-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|[Bb]earer\s+[A-Za-z0-9._-]{12,})/g;
const RETRYABLE = new Set([429, 500, 502, 503, 504]);

export function redact(text) {
  return String(text).replace(KEY_PATTERN, '[REDACTED]');
}

export class ModelError extends Error {
  constructor(message, status) {
    super(redact(message));
    this.status = status;
  }
}

export function schemaErrors(schema, value, where = 'arguments') {
  const errors = [];
  const type = schema.type;
  if (type && !TYPE_CHECKS[type](value)) return [`${where} must be ${type}`];
  if (schema.enum && !schema.enum.includes(value)) errors.push(`${where} must be one of ${schema.enum.join(', ')}`);
  if (type === 'object') {
    const props = schema.properties || {};
    for (const name of schema.required || []) if (!(name in value)) errors.push(`${where}.${name} is required`);
    for (const [name, item] of Object.entries(value)) {
      if (!(name in props)) errors.push(`${where}.${name} is not a known parameter`);
      else errors.push(...schemaErrors(props[name], item, `${where}.${name}`));
    }
  }
  if (type === 'array') value.forEach((item, i) => errors.push(...schemaErrors(schema.items || {}, item, `${where}[${i}]`)));
  if ((type === 'integer' || type === 'number') && schema.minimum !== undefined && value < schema.minimum) errors.push(`${where} must be >= ${schema.minimum}`);
  if ((type === 'integer' || type === 'number') && schema.maximum !== undefined && value > schema.maximum) errors.push(`${where} must be <= ${schema.maximum}`);
  return errors;
}

export class Tool {
  constructor(name, description, parameters, handler) {
    if (!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(name)) throw new Error(`tool name ${name} is not portable`);
    Object.assign(this, { name, description, parameters, handler });
  }
  spec() { return { name: this.name, description: this.description, parameters: this.parameters }; }
  async call(args) {
    const problems = schemaErrors(this.parameters, args);
    if (problems.length) return { ok: false, output: `invalid arguments for ${this.name}: ${problems.join('; ')}` };
    try {
      const result = await this.handler(args);
      return { ok: true, output: typeof result === 'string' ? result : JSON.stringify(result) };
    } catch (error) {
      return { ok: false, output: `tool ${this.name} failed: ${redact(error.message).slice(0, 500)}` };
    }
  }
}

export class ScriptedModel {
  constructor(replies) { this.replies = [...replies]; this.calls = []; }
  async complete(system, messages, tools) {
    this.calls.push({ system, messages: [...messages], tools });
    if (!this.replies.length) throw new ModelError('scripted model has no replies left');
    const reply = this.replies.shift();
    const toolCalls = (reply.tool_calls || []).map((c, i) => ({ id: c.id || `call_${this.calls.length}_${i}`, name: c.name, arguments: c.arguments || {}, validJson: true }));
    return { text: reply.text || '', toolCalls, stopReason: toolCalls.length ? 'tool_use' : 'stop' };
  }
}

function parseArguments(raw) {
  if (raw && typeof raw === 'object') return [raw, true];
  try {
    const value = JSON.parse(raw || '{}');
    return value && typeof value === 'object' && !Array.isArray(value) ? [value, true] : [raw, false];
  } catch {
    return [raw, false];
  }
}

const PORTABLE = new Set(['type', 'description', 'enum', 'properties', 'required', 'items', 'minimum', 'maximum', 'minItems', 'maxItems', 'minLength', 'maxLength']);
export function geminiSchema(schema) {
  const kept = {};
  for (const [key, value] of Object.entries(schema)) {
    if (!PORTABLE.has(key)) continue;
    if (key === 'properties') kept.properties = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, geminiSchema(v)]));
    else if (key === 'items') kept.items = geminiSchema(value);
    else kept[key] = value;
  }
  if (Array.isArray(kept.required) && kept.required.length === 0) delete kept.required;
  return kept;
}

class HttpAdapter {
  constructor({ baseUrl, model, apiKey = null, dryRun = false, maxRetries = 3, sleep = (ms) => new Promise((r) => setTimeout(r, ms)), maxTokens = 1024, fetchImpl = globalThis.fetch }) {
    Object.assign(this, { baseUrl: baseUrl.replace(/\/$/, ''), model, apiKey, dryRun, maxRetries, sleep, maxTokens, fetchImpl });
    this.lastRequest = null;
  }
  async complete(system, messages, tools) {
    const { url, headers, body } = this.buildRequest(system, messages, tools);
    const shown = Object.fromEntries(Object.entries(headers).map(([k, v]) => [k, /authorization|api-key/i.test(k) ? '[REDACTED]' : v]));
    this.lastRequest = { url, headers: shown, body };
    if (this.dryRun) return { text: '', toolCalls: [], stopReason: 'dry-run', raw: this.lastRequest };
    for (let attempt = 0; ; attempt++) {
      let response;
      try {
        response = await this.fetchImpl(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });
      } catch (error) {
        if (attempt < this.maxRetries) { await this.sleep(500 * 2 ** attempt); continue; }
        throw new ModelError(`${this.style} request failed: ${error.message}`);
      }
      if (response.ok) return this.parseResponse(await response.json());
      const detail = (await response.text()).slice(0, 400);
      if (RETRYABLE.has(response.status) && attempt < this.maxRetries) {
        const retryAfter = Number(response.headers.get('retry-after'));
        await this.sleep(Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : 500 * 2 ** attempt);
        continue;
      }
      throw new ModelError(`${this.style} returned HTTP ${response.status}: ${detail}`, response.status);
    }
  }
}

export class OpenAIChatAdapter extends HttpAdapter {
  get style() { return 'openai-chat'; }
  buildRequest(system, messages, tools) {
    const out = system ? [{ role: 'system', content: system }] : [];
    for (const m of messages) {
      if (m.role === 'assistant' && m.toolCalls?.length) {
        out.push({ role: 'assistant', content: m.content || null, tool_calls: m.toolCalls.map((c) => ({ id: c.id, type: 'function', function: { name: c.name, arguments: c.validJson ? JSON.stringify(c.arguments) : String(c.arguments) } })) });
      } else if (m.role === 'tool') out.push({ role: 'tool', tool_call_id: m.toolCallId, content: m.content });
      else out.push({ role: m.role, content: m.content });
    }
    const body = { model: this.model, messages: out };
    if (tools.length) body.tools = tools.map((t) => ({ type: 'function', function: t }));
    return { url: `${this.baseUrl}/chat/completions`, headers: this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}, body };
  }
  parseResponse(data) {
    const choice = data?.choices?.[0];
    if (!choice?.message) throw new ModelError(`unexpected chat completions response: ${JSON.stringify(data).slice(0, 300)}`);
    const toolCalls = (choice.message.tool_calls || []).map((c, i) => {
      const [args, ok] = parseArguments(c.function?.arguments);
      return { id: c.id || `call_${i}`, name: c.function?.name || '', arguments: args, validJson: ok };
    });
    return { text: choice.message.content || '', toolCalls, stopReason: choice.finish_reason || 'stop', raw: data };
  }
}

export class AnthropicAdapter extends HttpAdapter {
  get style() { return 'anthropic-messages'; }
  buildRequest(system, messages, tools) {
    const out = [];
    for (const m of messages) {
      if (m.role === 'tool') {
        const block = { type: 'tool_result', tool_use_id: m.toolCallId, content: m.content };
        const last = out[out.length - 1];
        if (last && last.role === 'user' && Array.isArray(last.content) && last.content.every((b) => b.type === 'tool_result')) last.content.push(block);
        else out.push({ role: 'user', content: [block] });
      } else if (m.role === 'assistant') {
        const blocks = m.content ? [{ type: 'text', text: m.content }] : [];
        for (const c of m.toolCalls || []) blocks.push({ type: 'tool_use', id: c.id, name: c.name, input: c.validJson ? c.arguments : {} });
        out.push({ role: 'assistant', content: blocks });
      } else out.push({ role: 'user', content: m.content });
    }
    const body = { model: this.model, max_tokens: this.maxTokens, messages: out };
    if (system) body.system = system;
    if (tools.length) body.tools = tools.map((t) => ({ name: t.name, description: t.description, input_schema: t.parameters }));
    const headers = { 'anthropic-version': '2023-06-01' };
    if (this.apiKey) headers['x-api-key'] = this.apiKey;
    return { url: `${this.baseUrl}/v1/messages`, headers, body };
  }
  parseResponse(data) {
    if (!Array.isArray(data?.content)) throw new ModelError(`unexpected messages response: ${JSON.stringify(data).slice(0, 300)}`);
    const text = data.content.filter((b) => b.type === 'text').map((b) => b.text).join('');
    const toolCalls = data.content.filter((b) => b.type === 'tool_use').map((b) => ({ id: b.id, name: b.name, arguments: b.input || {}, validJson: true }));
    return { text, toolCalls, stopReason: data.stop_reason || 'end_turn', raw: data };
  }
}

export class GeminiAdapter extends HttpAdapter {
  get style() { return 'gemini'; }
  buildRequest(system, messages, tools) {
    const contents = [];
    const namesById = {};
    for (const m of messages) {
      if (m.role === 'assistant') {
        const parts = m.content ? [{ text: m.content }] : [];
        for (const c of m.toolCalls || []) {
          namesById[c.id] = c.name;
          const functionCall = { name: c.name, args: c.validJson ? c.arguments : {} };
          if (!c.id.startsWith('gemini_')) functionCall.id = c.id;
          parts.push({ functionCall });
        }
        contents.push({ role: 'model', parts });
      } else if (m.role === 'tool') {
        const functionResponse = { name: namesById[m.toolCallId] || m.name || '', response: { result: m.content } };
        if (m.toolCallId && !m.toolCallId.startsWith('gemini_')) functionResponse.id = m.toolCallId;
        const last = contents[contents.length - 1];
        if (last && last.role === 'user' && last.parts.every((p) => p.functionResponse)) last.parts.push({ functionResponse });
        else contents.push({ role: 'user', parts: [{ functionResponse }] });
      } else contents.push({ role: 'user', parts: [{ text: m.content }] });
    }
    const body = { contents };
    if (system) body.systemInstruction = { parts: [{ text: system }] };
    if (tools.length) {
      body.tools = [{ functionDeclarations: tools.map((t) => {
        const params = geminiSchema(t.parameters);
        return params.properties && Object.keys(params.properties).length ? { name: t.name, description: t.description, parameters: params } : { name: t.name, description: t.description };
      }) }];
    }
    return { url: `${this.baseUrl}/v1beta/models/${encodeURIComponent(this.model)}:generateContent`, headers: this.apiKey ? { 'x-goog-api-key': this.apiKey } : {}, body };
  }
  parseResponse(data) {
    const candidate = data?.candidates?.[0];
    if (!candidate) throw new ModelError('no candidates in generateContent response');
    const parts = candidate.content?.parts || [];
    const text = parts.filter((p) => 'text' in p).map((p) => p.text).join('');
    const toolCalls = parts.map((p, i) => [p, i]).filter(([p]) => p.functionCall).map(([p, i]) => ({ id: p.functionCall.id || `gemini_${i}`, name: p.functionCall.name, arguments: p.functionCall.args || {}, validJson: true }));
    return { text, toolCalls, stopReason: candidate.finishReason || 'STOP', raw: data };
  }
}

export class SlidingWindowMemory {
  constructor(maxChars = 24000) { this.maxChars = maxChars; }
  window(messages) {
    const units = [];
    for (const m of messages) {
      const last = units[units.length - 1];
      if (m.role === 'tool' && last && (last[0].toolCalls?.length || last[last.length - 1].role === 'tool')) last.push(m);
      else units.push([m]);
    }
    const size = (unit) => unit.reduce((n, m) => n + (m.content || '').length + JSON.stringify(m.toolCalls || []).length, 0);
    const kept = [];
    let total = 0;
    for (let i = units.length - 1; i >= 0; i--) {
      const s = size(units[i]);
      if (kept.length && total + s > this.maxChars) break;
      kept.unshift(units[i]);
      total += s;
    }
    const flat = kept.flat();
    while (flat.length && flat[0].role === 'tool') flat.shift();
    return flat;
  }
}

export class Agent {
  constructor({ model, system = '', tools = [], maxSteps = 8, memory = null }) {
    Object.assign(this, { model, system, maxSteps, memory });
    this.tools = new Map(tools.map((t) => [t.name, t]));
    this.messages = [];
  }
  async run(userText) {
    this.messages.push({ role: 'user', content: userText });
    const specs = [...this.tools.values()].map((t) => t.spec());
    const log = [];
    for (let step = 1; step <= this.maxSteps; step++) {
      const window = this.memory ? this.memory.window(this.messages) : this.messages;
      let reply;
      try {
        reply = await this.model.complete(this.system, window, specs);
      } catch (error) {
        return { finalText: '', steps: step, toolCalls: log, stopReason: `error: ${error.message}`, messages: this.messages };
      }
      if (reply.stopReason === 'dry-run') return { finalText: '', steps: step, toolCalls: log, stopReason: 'dry-run', request: reply.raw, messages: this.messages };
      this.messages.push({ role: 'assistant', content: reply.text, toolCalls: reply.toolCalls });
      if (!reply.toolCalls.length) return { finalText: reply.text, steps: step, toolCalls: log, stopReason: 'final', messages: this.messages };
      for (const call of reply.toolCalls) {
        const tool = this.tools.get(call.name);
        let result;
        if (!tool) result = { ok: false, output: `unknown tool '${call.name}'; available: ${[...this.tools.keys()].join(', ')}` };
        else if (!call.validJson) result = { ok: false, output: `arguments for ${call.name} were not valid JSON; send a JSON object` };
        else result = await tool.call(call.arguments);
        log.push({ step, name: call.name, arguments: call.arguments, ok: result.ok });
        this.messages.push({ role: 'tool', content: result.output, toolCallId: call.id, name: call.name });
      }
    }
    return { finalText: '', steps: this.maxSteps, toolCalls: log, stopReason: 'max_steps', messages: this.messages };
  }
}
