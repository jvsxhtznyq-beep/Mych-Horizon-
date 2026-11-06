// node --test tests/js/chatkit.test.mjs  (also run by tests/test_spec_chatbot.py)
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { Agent, Tool, ScriptedModel, OpenAIChatAdapter, AnthropicAdapter, GeminiAdapter, SlidingWindowMemory, schemaErrors, redact } from '../../specialists/mych-chatbot-engineering/scripts/chatkit.mjs';

const add = new Tool('add', 'Add two numbers.', { type: 'object', properties: { a: { type: 'number' }, b: { type: 'number' } }, required: ['a', 'b'] }, ({ a, b }) => String(a + b));

function stub(handler) {
  const requests = [];
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      const parsed = body ? JSON.parse(body) : null;
      requests.push({ url: req.url, headers: req.headers, body: parsed });
      const [status, payload, headers = {}] = handler(req.url, parsed, requests.length);
      res.writeHead(status, { 'Content-Type': 'application/json', ...headers });
      res.end(JSON.stringify(payload));
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({ server, requests, url: `http://127.0.0.1:${server.address().port}` })));
}

test('agent runs a tool and returns the final answer', async () => {
  const model = new ScriptedModel([{ tool_calls: [{ name: 'add', arguments: { a: 2, b: 3 } }] }, { text: 'The sum is 5.' }]);
  const result = await new Agent({ model, tools: [add] }).run('What is 2+3?');
  assert.equal(result.stopReason, 'final');
  assert.equal(result.finalText, 'The sum is 5.');
  assert.deepEqual(result.toolCalls.map((c) => [c.name, c.ok]), [['add', true]]);
  assert.equal(model.calls[1].messages.at(-1).content, '5');
});

test('invalid arguments and unknown tools are returned to the model, not thrown', async () => {
  const model = new ScriptedModel([{ tool_calls: [{ name: 'add', arguments: { a: 'x' } }, { name: 'nope', arguments: {} }] }, { text: 'done' }]);
  const result = await new Agent({ model, tools: [add] }).run('go');
  assert.deepEqual(result.toolCalls.map((c) => c.ok), [false, false]);
  const toolMessages = model.calls[1].messages.filter((m) => m.role === 'tool').map((m) => m.content);
  assert.match(toolMessages[0], /invalid arguments for add/);
  assert.match(toolMessages[1], /unknown tool 'nope'/);
});

test('step limit stops endless tool loops', async () => {
  const replies = Array.from({ length: 5 }, () => ({ tool_calls: [{ name: 'add', arguments: { a: 1, b: 1 } }] }));
  const result = await new Agent({ model: new ScriptedModel(replies), tools: [add], maxSteps: 3 }).run('loop');
  assert.equal(result.stopReason, 'max_steps');
  assert.equal(result.toolCalls.length, 3);
});

for (const [name, Adapter, first, second, check] of [
  ['openai-chat', OpenAIChatAdapter,
    { choices: [{ message: { content: null, tool_calls: [{ id: 'c1', type: 'function', function: { name: 'add', arguments: '{"a":2,"b":3}' } }] }, finish_reason: 'tool_calls' }] },
    { choices: [{ message: { content: 'It is 5.' }, finish_reason: 'stop' }] },
    (reqs) => {
      assert.equal(reqs[0].url, '/v1/chat/completions');
      assert.equal(reqs[0].body.messages[0].role, 'system');
      assert.equal(reqs[0].body.tools[0].type, 'function');
      assert.equal(reqs[0].headers.authorization, 'Bearer sk-test-key-123456');
      assert.deepEqual(reqs[1].body.messages.at(-1), { role: 'tool', tool_call_id: 'c1', content: '5' });
    }],
  ['anthropic-messages', AnthropicAdapter,
    { content: [{ type: 'tool_use', id: 'tu1', name: 'add', input: { a: 2, b: 3 } }], stop_reason: 'tool_use' },
    { content: [{ type: 'text', text: 'It is 5.' }], stop_reason: 'end_turn' },
    (reqs) => {
      assert.equal(reqs[0].url, '/v1/messages');
      assert.equal(reqs[0].body.system, 'Be brief.');
      assert.ok(reqs[0].body.tools[0].input_schema);
      assert.equal(reqs[0].headers['x-api-key'], 'sk-test-key-123456');
      assert.deepEqual(reqs[1].body.messages.at(-1), { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'tu1', content: '5' }] });
    }],
  ['gemini', GeminiAdapter,
    { candidates: [{ content: { role: 'model', parts: [{ functionCall: { name: 'add', args: { a: 2, b: 3 } } }] }, finishReason: 'STOP' }] },
    { candidates: [{ content: { role: 'model', parts: [{ text: 'It is 5.' }] }, finishReason: 'STOP' }] },
    (reqs) => {
      assert.equal(reqs[0].url, '/v1beta/models/test-model:generateContent');
      assert.equal(reqs[0].body.systemInstruction.parts[0].text, 'Be brief.');
      assert.ok(reqs[0].body.tools[0].functionDeclarations[0].parameters);
      assert.equal(reqs[0].headers['x-goog-api-key'], 'sk-test-key-123456');
      assert.deepEqual(reqs[1].body.contents.at(-1), { role: 'user', parts: [{ functionResponse: { name: 'add', response: { result: '5' } } }] });
    }],
]) {
  test(`${name} adapter completes a two-step tool loop against a stub`, async () => {
    const { server, requests, url } = await stub((_url, _body, n) => [200, n === 1 ? first : second]);
    try {
      const base = name === 'openai-chat' ? `${url}/v1` : url;
      const adapter = new Adapter({ baseUrl: base, model: 'test-model', apiKey: 'sk-test-key-123456' });
      const result = await new Agent({ model: adapter, system: 'Be brief.', tools: [add] }).run('2+3?');
      assert.equal(result.finalText, 'It is 5.');
      check(requests);
    } finally {
      server.close();
    }
  });
}

test('429 with Retry-After is retried; malformed tool arguments become a tool error', async () => {
  const delays = [];
  const { server, url } = await stub((_u, _b, n) => {
    if (n === 1) return [429, { error: 'slow down' }, { 'Retry-After': '2' }];
    if (n === 2) return [200, { choices: [{ message: { tool_calls: [{ id: 'x', type: 'function', function: { name: 'add', arguments: '{bad json' } }] } }] }];
    return [200, { choices: [{ message: { content: 'ok' } }] }];
  });
  try {
    const adapter = new OpenAIChatAdapter({ baseUrl: url, model: 'm', sleep: async (ms) => { delays.push(ms); } });
    const result = await new Agent({ model: adapter, tools: [add] }).run('go');
    assert.deepEqual(delays, [2000]);
    assert.equal(result.toolCalls[0].ok, false);
    assert.equal(result.finalText, 'ok');
  } finally {
    server.close();
  }
});

test('dry run builds the request without sending and redacts the key', async () => {
  const adapter = new AnthropicAdapter({ baseUrl: 'https://example.invalid', model: 'm', apiKey: 'sk-live-secret-abcdef', dryRun: true });
  const result = await new Agent({ model: adapter, system: 's', tools: [add] }).run('hi');
  assert.equal(result.stopReason, 'dry-run');
  assert.equal(result.request.headers['x-api-key'], '[REDACTED]');
  assert.ok(!JSON.stringify(result.request).includes('sk-live-secret-abcdef'));
});

test('memory keeps tool calls with their results and respects the budget', () => {
  const messages = [
    { role: 'user', content: 'x'.repeat(50) },
    { role: 'assistant', content: '', toolCalls: [{ id: 'a', name: 'add', arguments: { a: 1, b: 2 } }] },
    { role: 'tool', content: '3', toolCallId: 'a' },
    { role: 'assistant', content: 'three' },
    { role: 'user', content: 'y'.repeat(20) },
  ];
  const window = new SlidingWindowMemory(70).window(messages);
  assert.equal(window[0].role, 'assistant');
  assert.ok(window.every((m, i) => m.role !== 'tool' || window[i - 1].toolCalls?.length));
  assert.ok(!window.includes(messages[0]));
});

test('schema and redaction helpers', () => {
  assert.deepEqual(schemaErrors({ type: 'object', properties: { n: { type: 'integer', minimum: 1 } }, required: ['n'] }, { n: 0 }), ['arguments.n must be >= 1']);
  assert.equal(redact('key sk-abcdefghijklmnop end'), 'key [REDACTED] end');
});
