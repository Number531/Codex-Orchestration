// Opt-in package integration: node test/native-smoke.mjs /absolute/path/to/codex
// Uses only a loopback scripted Responses provider. It does not call a paid model.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const binary = process.argv[2];
assert(binary && path.isAbsolute(binary), 'Supply the absolute Codex executable path.');
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'orchestration-native-project-')));
const init = spawnSync('git', ['init', '-q', root], { encoding: 'utf8' });
assert.equal(init.status, 0, init.stderr);
const install = spawnSync('python3', ['-B', path.join(packageRoot, 'scripts/setup.py'), '--project', root, '--apply'], { encoding: 'utf8' });
assert.equal(install.status, 0, install.stderr || install.stdout);
console.log(`Installed synthetic project: ${root}`);
const version = spawnSync(binary, ['--version'], { encoding: 'utf8' });
assert.equal(version.status, 0, version.stderr);
console.log(version.stdout.trim());
const flag = path.join(root, '.codex/delegation-guard.json');
const script = path.join(root, '.agents/system/hooks/delegation_guard.py');
const codexConfigDir = process.env.CODEX_HOME || path.join(os.homedir(), '.codex');
// Invocation-only trust bypass is limited to reviewed local hooks; fail on extra
// hook files. User config is ignored; managed configuration must be reviewed separately.
for (const file of [path.join(codexConfigDir, 'hooks.json'), '/etc/codex/hooks.json',
  '/etc/codex/requirements.toml', '/etc/codex/config.toml']) {
  assert(!fs.existsSync(file), `Review extra hook/managed source before running this pilot: ${file}`);
}
const config = JSON.parse(fs.readFileSync(path.join(root, '.codex/hooks.json')));
const projectFile = path.join(root, '.codex/config.toml');
function readAgentOverrides() {
  const projectRead = spawnSync('python3', ['-c', 'import json,sys,tomllib; print(json.dumps(tomllib.load(open(sys.argv[1],"rb"))["agents"]))', projectFile], { encoding: 'utf8' });
  assert.equal(projectRead.status, 0, projectRead.stderr);
  const projectAgents = JSON.parse(projectRead.stdout);
  // --ignore-user-config also removes the persisted project trust used for
  // registration. Mirror the reviewed project's actual agent settings, just as
  // the reviewed hook is supplied explicitly, without changing user config.
  const agentOverrides = [];
  for (const key of ['default_subagent_model', 'default_subagent_reasoning_effort']) {
    assert.equal(typeof projectAgents[key], 'string');
    agentOverrides.push('-c', `agents.${key}=${JSON.stringify(projectAgents[key])}`);
  }
  for (const [name, agent] of Object.entries(projectAgents)) {
    if (agent && typeof agent === 'object' && agent.config_file) {
      agentOverrides.push('-c', `agents.${name}.config_file=${JSON.stringify(path.resolve(root, '.codex', agent.config_file))}`);
      agentOverrides.push('-c', `agents.${name}.description=${JSON.stringify(agent.description)}`);
    }
  }
  return agentOverrides;
}
assert.deepEqual(Object.keys(config.hooks), ['PreToolUse']);
assert.equal(config.hooks.PreToolUse.length, 1);
assert.equal(config.hooks.PreToolUse[0].hooks.length, 1);
assert.equal(config.hooks.PreToolUse[0].hooks[0].command,
  'python3 "$(git rev-parse --show-toplevel)/.agents/system/hooks/delegation_guard.py"');
let original;
let fixtureCreated = false;
let originalProject;
let unboundCreated = false;
const fixture = path.join(root, '.codex/agents/delegation-guard-cost-fixture.toml');
assert(!fs.existsSync(fixture), 'Refusing to overwrite an existing fixture profile.');
const unboundFixture = path.join(root, '.codex/agents/delegation-guard-unbound-fixture.toml');
assert(!fs.existsSync(unboundFixture), 'Refusing to overwrite an existing unbound fixture profile.');
const group = config.hooks.PreToolUse[0];
const handler = group.hooks[0];
const hookOverride = `hooks.PreToolUse=[{matcher=${JSON.stringify(group.matcher)},hooks=[{type="command",command=${JSON.stringify(handler.command)},timeout=${handler.timeout}}]}]`;
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-guard-smoke-'));
const models = JSON.parse(fs.readFileSync(path.join(codexConfigDir, 'models_cache.json'))).models.filter(model => ['gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.6-sol', 'gpt-6-astra'].includes(model.slug));
assert(Array.isArray(models) && models.length, 'A local model catalog is required.');
const catalog = path.join(scratch, 'catalog.json');
fs.writeFileSync(catalog, JSON.stringify({ models }));
const results = [];
const CHILD_MARKER = 'DELEGATION_COST_FIXTURE_CHILD';
const base = { task_name: 'routing_fixture', agent_type: 'explorer',
  fork_turns: 'none', message: `${CHILD_MARKER}. Local fixture; reply done. Do not delegate.` };
const cases = [
  { name: 'named_luna', args: base, model: 'gpt-5.6-luna', effort: 'max' },
  { name: 'dynamic_default', args: { ...base, agent_type: 'default', task_name: 'investigate_any_task' }, model: 'gpt-5.6-luna', effort: 'max' },
  { name: 'omitted_role', args: Object.fromEntries(Object.entries(base).filter(([key]) => key !== 'agent_type')), model: 'gpt-5.6-luna', effort: 'max' },
  { name: 'dynamic_worker', args: { ...base, agent_type: 'worker', task_name: 'repair_any_task' }, model: 'gpt-5.6-terra', effort: 'high' },
  { name: 'named_terra', args: { ...base, agent_type: 'implementer' }, model: 'gpt-5.6-terra', effort: 'high' },
  { name: 'named_sol', args: { ...base, agent_type: 'auditor' }, model: 'gpt-5.6-sol', effort: 'high' },
  { name: 'named_verifier', args: { ...base, agent_type: 'verifier' }, model: 'gpt-5.6-terra', effort: 'medium' },
  { name: 'unregistered_cheap', args: { ...base, agent_type: 'unbound_fixture' }, deny: true },
  { name: 'bound_profile_name', args: { ...base, agent_type: 'native_name_fixture' }, model: 'gpt-5.6-terra', effort: 'high' },
  { name: 'legacy_alias', args: { ...base, agent_type: 'legacy_alias' }, deny: true },
  { name: 'custom_costly', args: { ...base, agent_type: 'cost_fixture' }, deny: true },
  { name: 'override', args: { ...base, model: 'gpt-5.6-terra' }, deny: true },
  { name: 'inheritance', args: { ...base, fork_turns: 'all' }, deny: true },
  { name: 'unknown', args: { ...base, agent_type: 'unregistered_fixture' }, deny: true },
  { name: 'retry_cheap', args: { ...base, agent_type: 'cost_fixture' }, retry: true, model: 'gpt-5.6-terra', effort: 'high' },
  { name: 'off_astra', off: true, args: { ...base, agent_type: 'cost_fixture' }, model: 'gpt-6-astra', effort: 'max' },
  { name: 'sandbox_integrity', args: { ...base, agent_type: 'worker' }, probe: true, model: 'gpt-5.6-terra', effort: 'high' },
];
// A harmless positive control plus protected-directory sentinel attempts. No
// existing files are edited, even if a client unexpectedly permits the writes.
const probeCode = `from pathlib import Path
import tempfile
root=Path.cwd()
for label,directory in [('workspace',root),('policy',root/'.codex'),('guard',root/'.agents/system/hooks')]:
 try:
  with tempfile.NamedTemporaryFile(prefix='cost-guard-permission-probe-',dir=directory): pass
  print(label+'=writable')
 except PermissionError: print(label+'=protected')`;
const probeCommand = 'python3 -c ' + "'" + probeCode.replaceAll("'", "'\\''") + "'";
let activeChild;
let interrupted;
function stopChild(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  child.kill('SIGTERM');
  const force = setTimeout(() => child.kill('SIGKILL'), 1500);
  force.unref();
  child.once('exit', () => clearTimeout(force));
}
function interrupt(signal) {
  interrupted = new Error(`Runtime fixture interrupted by ${signal}`);
  stopChild(activeChild);
}
const signals = ['SIGINT', 'SIGTERM'].map(signal => {
  const handler = () => interrupt(signal);
  process.on(signal, handler);
  return [signal, handler];
});
function probeItem(body) {
  const definitions = [...(body.tools || []), ...(body.input || []).filter(x => x.type === 'additional_tools').flatMap(x => x.tools || [])];
  assert(definitions.some(d => d.name === 'functions' && d.tools?.some(t => t.name === 'exec' && t.type === 'custom')), 'Native functions.exec tool is unavailable.');
  const command = { cmd: probeCommand, workdir: root, max_output_tokens: 1000 };
  return { id: 'fc_probe', type: 'custom_tool_call', namespace: 'functions', name: 'exec', call_id: 'probe_call',
    input: `text(await tools.exec_command(${JSON.stringify(command)}));` };
}

async function runCase(test) {
  if (interrupted) throw interrupted;
  const { name, args: spawnArgs, deny: denied } = test;
  const on = !test.off;
  const toggle = spawnSync('python3', [script, on ? '--on' : '--off'], { encoding: 'utf8' });
  assert.equal(toggle.status, 0, toggle.stderr);
  let called = false;
  let waited = false;
  let toolResult = '';
  let retryResult = '';
  let retried = false;
  let probeCalled = false;
  let probeOutput = '';
  const requests = [];
  let timedOut = false;
  let childModel = null;
  let childEffort = null;
  let requestCount = 0;
  let running;
  let serverError;
  const server = http.createServer(async (req, res) => {
    try {
      let raw = '';
      for await (const chunk of req) { raw += chunk; assert(raw.length <= 4 * 1024 * 1024, 'Fixture request too large.'); }
      if (req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ models }));
        return;
      }
      const body = JSON.parse(process.argv.includes('--inject-request-error') ? '{' : raw);
      assert(++requestCount <= 16, 'Unexpected model loop.');
      // Fresh child task messages carry a marker; tool arguments in the parent
      // history do not count. This also detects a forbidden child on Astra.
      const child = (body.input || []).some(x => x.type === 'agent_message' && x.author === '/root' && x.recipient !== '/root' && JSON.stringify(x).includes(CHILD_MARKER));
      requests.push({ child, model: body.model, effort: body.reasoning?.effort });
      if (child) { childModel = body.model; childEffort = body.reasoning?.effort; }
      const outputs = (body.input || []).filter(x => x.type === 'function_call_output' && x.call_id === 'guard_call');
      if (outputs.length) toolResult = String(outputs.at(-1).output);
      const retryOutputs = (body.input || []).filter(x => x.type === 'function_call_output' && x.call_id === 'retry_call');
      if (retryOutputs.length) retryResult = String(retryOutputs.at(-1).output);
      const probeOutputs = (body.input || []).filter(x => ['function_call_output', 'custom_tool_call_output'].includes(x.type) && x.call_id === 'probe_call');
      if (probeOutputs.length) probeOutput = JSON.stringify(probeOutputs.at(-1).output);
      let item;
      if (!called && !child) {
        called = true;
        item = { id: 'fc_guard', type: 'function_call', namespace: 'collaboration',
          name: 'spawn_agent', call_id: 'guard_call', arguments: JSON.stringify(spawnArgs) };
      } else if (!child && test.retry && !retried) {
        assert.match(toolResult, /blocked by PreToolUse hook: Delegation guard:/);
        assert.equal(childModel, null, 'No child request before denied call is retried.');
        retried = true;
        item = { id: 'fc_retry', type: 'function_call', namespace: 'collaboration',
          name: 'spawn_agent', call_id: 'retry_call', arguments: JSON.stringify({ ...base, agent_type: 'worker' }) };
      } else if (child && test.probe && !probeCalled) {
        probeCalled = true;
        item = probeItem(body);
      } else if (!child && !denied && !waited) {
        waited = true;
        item = { id: 'fc_wait', type: 'function_call', namespace: 'collaboration',
          name: 'wait_agent', call_id: 'wait_call', arguments: JSON.stringify({ timeout_ms: 10000 }) };
      } else {
        item = { id: 'msg_guard', type: 'message', role: 'assistant',
          content: [{ type: 'output_text', text: 'Routing fixture complete.' }] };
      }
      res.writeHead(200, { 'Content-Type': 'text/event-stream' });
      res.write(`data: ${JSON.stringify({ type: 'response.output_item.done', output_index: 0, item })}\n\n`);
      res.end(`data: ${JSON.stringify({ type: 'response.completed', response: {
        id: 'resp_guard', object: 'response', status: 'completed', output: [item],
        usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 },
      } })}\n\n`);
    } catch (error) {
      // EventEmitter does not await async handlers. Route failures back through
      // the awaited process exit so the outer flag-restoration finally runs.
      serverError ??= error;
      res.destroy();
      stopChild(running);
    }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const args = ['exec', '--ignore-user-config', '--json', '-s', test.probe ? 'workspace-write' : 'read-only', '-C', root,
    '--enable', 'multi_agent_v2', '--dangerously-bypass-hook-trust',
    '-c', hookOverride,
    ...readAgentOverrides(),
    '-c', `projects.${JSON.stringify(root)}.trust_level="trusted"`,
    '-c', `model_catalog_json=${JSON.stringify(catalog)}`, '-c', 'model="gpt-6-astra"',
    '-c', 'model_reasoning_effort="medium"', '-c', 'model_provider="routing_fixture"',
    '-c', 'model_providers.routing_fixture.name="Loopback routing fixture"',
    '-c', `model_providers.routing_fixture.base_url="http://127.0.0.1:${server.address().port}/v1"`,
    '-c', 'model_providers.routing_fixture.wire_api="responses"',
    '-c', 'model_providers.routing_fixture.requires_openai_auth=false',
    '-c', 'analytics.enabled=false', '-c', 'feedback.enabled=false',
    'Local scripted routing test. No application work is requested.'];
  // Use a normal local session for allowed V2 spawns; ephemeral parents were
  // unsupported in the original pilot. Synthetic session IDs identify local logs.
  if (denied) args.splice(1, 0, '--ephemeral');
  const child = activeChild = running = spawn(binary, args, { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  child.stdout.on('data', d => { stdout += d; });
  child.stderr.on('data', d => { stderr += d; });
  const timer = setTimeout(() => { timedOut = true; stopChild(child); }, 45000);
  let code;
  try { code = await new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', resolve); }); }
  finally { activeChild = null; clearTimeout(timer); server.closeAllConnections(); await new Promise(r => server.close(r)); }
  const events = stdout.split('\n').filter(Boolean).flatMap(line => { try { return [JSON.parse(line)]; } catch { return []; } });
  const session = events.find(x => x.type === 'thread.started')?.thread_id;
  const diagnostics = stderr.split('\n').filter(line => /trust|disabled|config.toml/i.test(line));
  const summary = { name, code, session, toolResult, retryResult, childModel, childEffort, probeOutput, requests, diagnostics };
  console.log(JSON.stringify(summary));
  results.push(summary);
  if (serverError) throw serverError;
  if (interrupted) throw interrupted;
  assert(!timedOut, 'Native fixture exceeded 45 seconds.');
  assert.equal(code, 0, stderr.slice(-1500));
  if (denied) {
    assert.match(toolResult, /blocked by PreToolUse hook: Delegation guard:/);
    assert.equal(childModel, null, 'Denied spawn must not reach the model endpoint.');
  } else {
    assert.doesNotMatch(test.retry ? retryResult : toolResult, /Delegation guard:|failed|error/i);
    assert.equal(childModel, test.model);
    assert.equal(childEffort, test.effort);
    assert(requests.filter(x => x.child).every(x => x.model === test.model && x.effort === test.effort));
    if (test.probe) {
      for (const expected of ['workspace=writable', 'policy=protected', 'guard=protected']) assert(probeOutput.includes(expected), probeOutput);
    }
  }
}

try {
  const aliased = path.join(root, '.codex/agents/native-name-fixture.toml');
  fs.writeFileSync(aliased, 'name="native_name_fixture"\ndescription="Native alias fixture"\nmodel="gpt-5.6-terra"\nmodel_reasoning_effort="high"\nsandbox_mode="read-only"\ndeveloper_instructions="Reply done. Do not delegate."\n', { flag: 'wx' });
  fs.appendFileSync(projectFile, '\n[agents.legacy_alias]\ndescription="Native alias fixture"\nconfig_file="agents/native-name-fixture.toml"\n');
  fs.writeFileSync(fixture, 'name="cost_fixture"\ndescription="Local expensive-model denial fixture"\nmodel="gpt-6-astra"\nmodel_reasoning_effort="max"\ndeveloper_instructions="Reply done; do not call tools or delegate."\n', { flag: 'wx' });
  fixtureCreated = true;
  original = fs.readFileSync(flag);
  originalProject = fs.readFileSync(projectFile);
  assert(!/^\[agents\.(?:cost_fixture|unbound_fixture)\]/m.test(originalProject.toString()), 'Fixture registration conflicts with existing config.');
  fs.appendFileSync(projectFile, '\n[agents.cost_fixture]\ndescription="Local expensive-model denial fixture"\nconfig_file="agents/delegation-guard-cost-fixture.toml"\n');
  fs.writeFileSync(unboundFixture, 'name="unbound_fixture"\ndescription="Unregistered cheap profile regression"\nmodel="gpt-5.6-luna"\nmodel_reasoning_effort="max"\ndeveloper_instructions="Reply done; no tools or delegation."\n', { flag: 'wx' });
  unboundCreated = true;
  const only = process.argv.find(x => x.startsWith('--case='))?.slice(7);
  const selected = only ? cases.filter(x => x.name === only) : cases;
  assert(selected.length, 'Unknown runtime case.');
  for (const entry of selected) await runCase(entry);
  console.log(`PASS: ${selected.length} sequential runtime cost-routing cases.`);
} finally {
  if (original) fs.writeFileSync(flag, original);
  if (originalProject) fs.writeFileSync(projectFile, originalProject);
  if (fixtureCreated) fs.unlinkSync(fixture);
  if (unboundCreated) fs.unlinkSync(unboundFixture);
  for (const [signal, handler] of signals) process.off(signal, handler);
  fs.writeFileSync(path.join(scratch, 'results.json'), JSON.stringify(results, null, 2));
  console.log(`Runtime evidence: ${path.join(scratch, 'results.json')}`);
}
