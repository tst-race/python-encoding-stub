# Python Encoding Stub

A source-only starting point for a Raceboat `IEncodingComponent` implemented in
Python. It is intentionally **not a working codec**: metadata is unset and both
codec hooks raise `NotImplementedError`. No transport, service credentials, CLI
codec subprocesses, or C++ wrapper are included.

## Generate a Plugin

From the RACEGEN root, supply values from the approved design and benchmark:

```bash
python3 plugins/python-encoding-stub/new_encoding.py \
  --name MyCodec \
  --mime-type image/png \
  --max-bytes 4096 \
  --encoding-time-seconds 1.0 \
  --out ./myCodec-encoding
```

These are illustrative values, not capacity or timing claims. The destination
must not exist and must be outside this template. Generation derives the package
and class `PluginMyCodecEncoding`, encoding id `myCodec`, and manifest together.
It does not initialize Git. Generated projects retain these development
instructions; use their own generated names rather than the template names below.

## Implement the Codec

- `source/PluginPythonStubEncoding/codec.py`: implement `encode(payload, parameters)`
  and `decode(content, parameters)` by importing the chosen Python library. Both
  accept native `bytes` and the `EncodingParameters.json` string, and must return
  native `bytes`. Parse and validate the parameter JSON here as needed.
- `source/PluginPythonStubEncoding/plugin.py`: the API adapter, factory, SDK state
  notification, SWIG byte-vector conversion, capacity checks, callbacks, and
  opt-in encoded-output persistence.
- `source/PluginPythonStubEncoding/metadata.json`: MIME type, raw payload capacity,
  encoding id, and pessimistic encoding time in seconds. The scheduler compares
  `now + encodingTime` with action timestamps in
  `raceboat/source/decomposed/ComponentPackageManager.cpp::isTimeToEncode`.
- `source/manifest.json`: encoding-only Python registration. `python_class` is
  included because the current `PluginDef.cpp` parser requires it even for
  decomposed components; the loader calls the module's four-argument
  `createEncoding(name, sdk, roleName, pluginConfig)` factory.

Import your library normally inside `codec.py`, for example `import your_codec`;
do not shell out to a Python executable. Pin its distribution and dependencies
in requirements.txt and install them in the matching Raceboat runtime image.
Native extensions must match that runtime's Python ABI, architecture, and OS.
`commsPluginBindings` and `_commsPluginBindings` come from Raceboat, not pip; do
not copy or edit the generated bindings. Python plugin support must be enabled
in the framework build.

The adapter copies `pluginConfig.pluginDirectory` and `loggingDirectory` rather
than retaining the loader's temporary config wrapper. Copy any other config
strings needed by a codec during construction. The loader owns component lifetime; do not add a
Python `destroyEncoding` or manually disown the component. Use SDK user-input
requests and `onUserInputReceived` if configuration requires them.

### Save encoded output for offline analysis

The adapter requests `save-encoded-output` as an optional user setting. It
defaults to false; declined, unanswered, or invalid input leaves persistence
disabled. When enabled, each successful encode writes the exact encoded bytes
to `<pluginConfig.loggingDirectory>/encoding-outputs/encoded-output-<handle>-<unique>.bin`.
Decode output is not saved. If saving was explicitly enabled but the file
cannot be written, the encode reports failure. Payload bytes are never logged.

For integration tests, declare `save-encoded-output` as a boolean with default
false in the dedicated composition's `channel_parameters`, with `plugin` set to
that composition ID. Set `<composition-id>.save-encoded-output=true` in each
integration node's `NodeContribution.params`. Do not change the default in the
generated plugin. Use synthetic data and treat saved output as test data that
requires appropriate access and cleanup.

Each accepted operation issues exactly one completion callback using its original
handle. Codec exceptions, invalid return types, and capacity violations produce
`ENCODE_FAILED` and `COMPONENT_ERROR`. SDK callback exceptions are not caught and
reported a second time. No payloads or parameters are logged. The default methods
run synchronously; move expensive work to a bounded worker if necessary and keep
the same completion contract. The current capacity is constant across parameter
sets: replace `getEncodingPropertiesForParameters` and the matching enforcement
if the selected codec has parameter-dependent capacity.

## Test and Stage

The scaffold needs only the Python standard library for its contract tests:

```bash
cd plugins/python-encoding-stub
bash run_unit_tests.sh -v
```

These tests use an explicit bindings double and patched codec hooks. Passing does
not establish a working codec or framework integration. Generator tests also
generate a temporary project, run its tests, and verify both staged kit layouts.

Run the separate real-SWIG smoke check in a matching Raceboat runtime with SDK
Python modules on `PYTHONPATH` and SDK shared libraries on `LD_LIBRARY_PATH`:

```bash
bash run_unit_tests.sh --real-bindings
```

This checks real SWIG types and Python-side SDK callbacks using test-only codec
hooks; it is not a C++ director, loader, or transport integration test. Binding import errors are fatal,
never replaced with a fake SDK. Use the same image tag for build/runtime gates.

From a generated project, stage the source-only client and server kits:

```bash
bash build_artifacts.sh --arch x86_64
```

Use `arm64-v8a` for Linux ARM64. There is no CMake or compilation step for pure
Python. The kit layout is
`kit/artifacts/linux-<arch>-{client,server}/<Package>/manifest.json`, with
`__init__.py`, `plugin.py`, `codec.py`, and metadata.json directly alongside the
manifest. The kit root above `<Package>` is the loader's module search directory.
Dependencies are not silently installed or vendored by this command;
requirements.txt is copied as an installation inventory. Staging rebuilds only
this plugin's output directory, and refuses unset template metadata. It does not
prove that codec hooks have been implemented.

Before calling a generated plugin complete, add actual library round-trip tests
for empty input, all byte values, random binary payloads, malformed content,
parameter validation, and exact capacity / capacity+1 boundaries. Benchmark the
target runtime and record conditions; do not claim lossy formats recover arbitrary
bytes without proof. Register a dedicated composition using `twoSixIndirect` and
the new encoding, then pass the initial integration gate. Later test a transport
that accepts the declared MIME type. Keep framework-owned examples unchanged.