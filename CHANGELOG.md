# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [v3.0.0](https://github.com/nexios-labs/Nexios/releases/tag/v3.0.0) - 2025-11-01

<small>[Compare with v2.11.13](https://github.com/nexios-labs/Nexios/compare/v2.11.13...v3.0.0)</small>

### Fixed

- fix(response):  return the streamed response instead of nexios response manager for the call_next function manager ([9c7bb62](https://github.com/nexios-labs/Nexios/commit/9c7bb62e140f497382d5768abbcfef1b2400b230) by techwithdunamix).
- fix docs inconsistencies #197 ([091f536](https://github.com/nexios-labs/Nexios/commit/091f53601421e3ffff8eda1ddfba7d87f0420036) by dunamix 🦄).
- fix: correct the use of process.nextTick ([964dd41](https://github.com/nexios-labs/Nexios/commit/964dd41bf62a1a8d38677d84c450b3cc4a199277) by techwithdunamix).
- fix(pagination): enhance cursor decoding and error handling ([c557a9c](https://github.com/nexios-labs/Nexios/commit/c557a9c7514bca3b79221187a2d2bb8172c0e0c6) by techwithdunamix).
- fix(auth): replace delete_session with del for session management ([329ad1f](https://github.com/nexios-labs/Nexios/commit/329ad1f8411dee1a7e42e084486c6b0166d8291c) by techwithdunamix).
- fix(session);: fix session clear method ([ac0277a](https://github.com/nexios-labs/Nexios/commit/ac0277a530c736c0db4c4cec5d0a19ad29edadfd) by techwithdunamix).
- fix(cors): improve CORS middleware and error handling ([d632ec9](https://github.com/nexios-labs/Nexios/commit/d632ec96f1c0414f182eb6abd9777fd6bf1754b8) by techwithdunamix).
- fix(middleware/cors): improve CORS method validation and preflight handling ([8aa71ab](https://github.com/nexios-labs/Nexios/commit/8aa71ab388fe331003693d80d66fee1794782a87) by techwithdunamix).
- fix(dependencies): remove unused context injection code ([6edc2f4](https://github.com/nexios-labs/Nexios/commit/6edc2f42e4b6a7bb14e2bc88399956aba06fd28d) by techwithdunamix).
- fix(routing): correctly prefix HTTP endpoint paths in OpenAPI documentation ([e285b6e](https://github.com/nexios-labs/Nexios/commit/e285b6ea53b53195cb2f70c7006e6be69a0ce1a4) by techwithdunamix).
- fix(http): correct expires header to use UTC time ([471aea6](https://github.com/nexios-labs/Nexios/commit/471aea61c9415a4c740d86e4d12a12f2f426cd26) by techwithdunamix).
- fix(http): use set_header method to manage response headers ([dcf17bb](https://github.com/nexios-labs/Nexios/commit/dcf17bb449f96766b0558a34ff29966f400d63b1) by techwithdunamix).
- fix: fix url_for nested routes tests: add tests for routing ([afa3dae](https://github.com/nexios-labs/Nexios/commit/afa3daec0f06c588e9192b4bbd8d3d447270d1f9) by techwithdunamix).
- fix(auth): resolve import issues and improve authentication handling ([78034ec](https://github.com/nexios-labs/Nexios/commit/78034ec49d86f894b41f574c867e4f1ccd65050f) by techwithdunamix).

## [v2.11.13](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.13) - 2025-10-07

<small>[Compare with v2.11.12](https://github.com/nexios-labs/Nexios/compare/v2.11.12...v2.11.13)</small>

## [v2.11.12](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.12) - 2025-10-07

<small>[Compare with v2.11.11](https://github.com/nexios-labs/Nexios/compare/v2.11.11...v2.11.12)</small>

## [v2.11.11](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.11) - 2025-10-07

<small>[Compare with v2.11.10](https://github.com/nexios-labs/Nexios/compare/v2.11.10...v2.11.11)</small>

### Fixed

- fix(routing): improve error handling for existing routes and update documentation ([4472b3c](https://github.com/nexios-labs/Nexios/commit/4472b3ca89d6a9e289e792acb2834557421d58c7) by techwithdunamix).

## [v2.11.10](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.10) - 2025-10-04

<small>[Compare with v2.11.9](https://github.com/nexios-labs/Nexios/compare/v2.11.9...v2.11.10)</small>

## [v2.11.9](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.9) - 2025-10-03

<small>[Compare with v2.11.8](https://github.com/nexios-labs/Nexios/compare/v2.11.8...v2.11.9)</small>

### Fixed

- fix: Fix all pytest warnings ([32e49ca](https://github.com/nexios-labs/Nexios/commit/32e49ca2ad94b4f45e8a448d4ca95a792e9629ce) by dmb225).

## [v2.11.8](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.8) - 2025-10-02

<small>[Compare with v2.11.7](https://github.com/nexios-labs/Nexios/compare/v2.11.7...v2.11.8)</small>

### Fixed

- fix(routing): add request_content_type parameter to Route and Router classes ([556ae46](https://github.com/nexios-labs/Nexios/commit/556ae46d2120525e381ebc001045dcb5adabcc04) by techwithdunamix).

## [v2.11.7](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.7) - 2025-10-01

<small>[Compare with v2.11.6](https://github.com/nexios-labs/Nexios/compare/v2.11.6...v2.11.7)</small>

### Fixed

- fix(params):  fix params mismatch ([6c61b4d](https://github.com/nexios-labs/Nexios/commit/6c61b4d70fbf85780d8e5195754928bc8fd54a3f) by techwithdunamix).

## [v2.11.6](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.6) - 2025-10-01

<small>[Compare with v2.11.5](https://github.com/nexios-labs/Nexios/compare/v2.11.5...v2.11.6)</small>

## [v2.11.5](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.5) - 2025-10-01

<small>[Compare with v2.11.4](https://github.com/nexios-labs/Nexios/compare/v2.11.4...v2.11.5)</small>

## [v2.11.4](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.4) - 2025-09-24

<small>[Compare with v2.11.3](https://github.com/nexios-labs/Nexios/compare/v2.11.3...v2.11.4)</small>

### Fixed

- fix(dependencies): improve context passing to dependencies ([a2b68fa](https://github.com/nexios-labs/Nexios/commit/a2b68fa4290388c444bfb1d23925dac9cb109c13) by techwithdunamix).
- fix(templating): update context only if middleware provides it ([8dc1712](https://github.com/nexios-labs/Nexios/commit/8dc1712e8f840992c8349893d61c4d7f56e14145) by techwithdunamix).

## [v2.11.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.3) - 2025-09-16

<small>[Compare with v2.11.2](https://github.com/nexios-labs/Nexios/compare/v2.11.2...v2.11.3)</small>

### Fixed

- fix(application): check returned state before updating app state ([3bb457b](https://github.com/nexios-labs/Nexios/commit/3bb457b554059550f8f4b30c50b28cbcd789cff8) by techwithdunamix).

## [v2.11.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.2) - 2025-09-14

<small>[Compare with v2.11.1](https://github.com/nexios-labs/Nexios/compare/v2.11.1...v2.11.2)</small>

### Fixed

- fix(http): remove debug prints and improve UploadedFile class ([acd274b](https://github.com/nexios-labs/Nexios/commit/acd274bcf815a941851ef9e3b859e2da07e2964b) by techwithdunamix).

## [v2.11.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.1) - 2025-09-10

<small>[Compare with v2.11.0](https://github.com/nexios-labs/Nexios/compare/v2.11.0...v2.11.1)</small>

### Fixed

- fix(_response_transformer): remove None type from json response check ([c81d5ec](https://github.com/nexios-labs/Nexios/commit/c81d5ec0eacecf8da6cf79fc13ce75bfcfcc5738) by techwithdunamix).
- fix(auth): update logging method in middleware ([2e086ea](https://github.com/nexios-labs/Nexios/commit/2e086eaf45c0f2f0baed7d46ecd4f88ee3ae92e7) by techwithdunamix).

## [v2.11.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.11.0) - 2025-09-06

<small>[Compare with v2.10.3](https://github.com/nexios-labs/Nexios/compare/v2.10.3...v2.11.0)</small>

## [v2.10.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.10.3) - 2025-08-28

<small>[Compare with v2.10.2](https://github.com/nexios-labs/Nexios/compare/v2.10.2...v2.10.3)</small>

### Fixed

- fix(docs): correct logging_middleware function parameters ([d8705b9](https://github.com/nexios-labs/Nexios/commit/d8705b999e15bd2770c1b54ea33189c5a0b807c9) by techwithdunamix).

## [v2.10.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.10.2) - 2025-08-16

<small>[Compare with v2.10.1](https://github.com/nexios-labs/Nexios/compare/v2.10.1...v2.10.2)</small>

### Fixed

- fix(auth): add Callable import to jwt backend ([694ad92](https://github.com/nexios-labs/Nexios/commit/694ad92b3ce138465cc0c99743df6c53a52ddc6b) by techwithdunamix).
- fix(request): change request.json() to request.json ([9b1524b](https://github.com/nexios-labs/Nexios/commit/9b1524bb0ac72dc66c56028fb0063f3bf38560f7) by techwithdunamix).

## [v2.10.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.10.1) - 2025-08-07

<small>[Compare with v2.10.0](https://github.com/nexios-labs/Nexios/compare/v2.10.0...v2.10.1)</small>

### Fixed

- fix(csrf): improve CSRF protection and token handling ([e7c910f](https://github.com/nexios-labs/Nexios/commit/e7c910fb47730f0a56a651cfab3b728766bdbb87) by techwithdunamix).
- fix(docs): fix routing docs orgnization ([4f0cfe4](https://github.com/nexios-labs/Nexios/commit/4f0cfe45c363eb63a9cf5d860f8a0cf4e893dec1) by techwithdunamix).
- fix(docs):  fix websockets documentation on channels ([bcdadd4](https://github.com/nexios-labs/Nexios/commit/bcdadd4ab434fea9282cdfe981a64bb0fb34968b) by techwithdunamix).
- fix(docs) : fix vitepress sytax issues ([f92ca86](https://github.com/nexios-labs/Nexios/commit/f92ca862b1711248ae24677e8bdceaf204f71bd0) by techwithdunamix).

## [v2.10.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.10.0) - 2025-08-02

<small>[Compare with v2.9.3](https://github.com/nexios-labs/Nexios/compare/v2.9.3...v2.10.0)</small>

### Fixed

- fix(docs) : imrpove clarity in authentication docs ([6d52a73](https://github.com/nexios-labs/Nexios/commit/6d52a737bdd98d7877da34d40e56ce3c1cdb8a9d) by techwithdunamix).
- fix(docs): fix issues in docs ([335dbde](https://github.com/nexios-labs/Nexios/commit/335dbde1b2fa8150ba197f1892cd0952cf4c2584) by techwithdunamix).

## [v2.9.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.9.3) - 2025-07-30

<small>[Compare with v2.9.2](https://github.com/nexios-labs/Nexios/compare/v2.9.2...v2.9.3)</small>

### Fixed

- fix (docs) : fix docs on nexios authetication docs ([b678cfd](https://github.com/nexios-labs/Nexios/commit/b678cfd16f192c254577f3dfcc78f5c0683360b5) by techwithdunamix).

## [v2.9.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.9.2) - 2025-07-28

<small>[Compare with v2.9.1](https://github.com/nexios-labs/Nexios/compare/v2.9.1...v2.9.2)</small>

## [v2.9.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.9.1) - 2025-07-27

<small>[Compare with v2.9.0](https://github.com/nexios-labs/Nexios/compare/v2.9.0...v2.9.1)</small>

### Fixed

- Fix(internals): now only inject depency once and just pass wrap handlers directly ([3603297](https://github.com/nexios-labs/Nexios/commit/3603297b5d123fd28d31bddc64eaa486c42d3c3c) by techwithdunamix).
- fix: clean up formatting in index.md and remove unnecessary whitespace ([0f3a05e](https://github.com/nexios-labs/Nexios/commit/0f3a05e6098f24f45aaa85d1d5ae7665f985971f) by techwithdunamix).
- fix: remove duplicate entry for granian in requirements.txt ([c4cca7e](https://github.com/nexios-labs/Nexios/commit/c4cca7e6319ef5ff9e1430357f5004654020e01f) by techwithdunamix).

## [v2.9.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.9.0) - 2025-07-23

<small>[Compare with v2.8.6](https://github.com/nexios-labs/Nexios/compare/v2.8.6...v2.9.0)</small>

### Fixed

- Fix #163 using logic from PR #164 ([93ddaff](https://github.com/nexios-labs/Nexios/commit/93ddaff446bc1036dd73bf758197f0ea36400b58) by techwithdunamix).
- fix: ensure proper handling of async and sync handlers in inject_dependencies function ([9c16653](https://github.com/nexios-labs/Nexios/commit/9c166533f616b0f7b96fa92f431c5596335ae8ed) by techwithdunamix).
- fix: update user type annotation from User to BaseUser in Context class ([0625030](https://github.com/nexios-labs/Nexios/commit/06250303bd40dded62b185a6ac42d5aa0983358c) by techwithdunamix).

## [v2.8.6](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.6) - 2025-07-18

<small>[Compare with v2.8.5](https://github.com/nexios-labs/Nexios/compare/v2.8.5...v2.8.6)</small>

## [v2.8.5](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.5) - 2025-07-18

<small>[Compare with v2.8.4](https://github.com/nexios-labs/Nexios/compare/v2.8.4...v2.8.5)</small>

## [v2.8.4](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.4) - 2025-07-18

<small>[Compare with v2.8.3](https://github.com/nexios-labs/Nexios/compare/v2.8.3...v2.8.4)</small>

### Fixed

- fix: improve CSRF token handling and enhance security middleware defaults ([1164bc9](https://github.com/nexios-labs/Nexios/commit/1164bc92072722f08ec58984193ed8a1685d5cbd) by techwithdunamix).

## [v2.8.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.3) - 2025-07-18

<small>[Compare with v2.8.2](https://github.com/nexios-labs/Nexios/compare/v2.8.2...v2.8.3)</small>

### Fixed

- fix: initialize _session_cache in BaseSessionInterface constructor ([ebf905c](https://github.com/nexios-labs/Nexios/commit/ebf905cd10f8782316987919101f78027bfa8ad4) by techwithdunamix).

## [v2.8.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.2) - 2025-07-18

<small>[Compare with v2.8.0](https://github.com/nexios-labs/Nexios/compare/v2.8.0...v2.8.2)</small>

### Fixed

- fix: update build command in release workflow ([1e27d0d](https://github.com/nexios-labs/Nexios/commit/1e27d0d1f1405124e9d917ab377fa6cd892d79b3) by techwithdunamix).

## [v2.8.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.8.0) - 2025-07-15

<small>[Compare with v2.7.0](https://github.com/nexios-labs/Nexios/compare/v2.7.0...v2.8.0)</small>

### Fixed

- fix: update release and triage workflows for consistency ([62335c4](https://github.com/nexios-labs/Nexios/commit/62335c451f48d1e450a3e8184e412b090203cc28) by techwithdunamix).
- fix: resolve issues with dependency merging in Router class ([09735cf](https://github.com/nexios-labs/Nexios/commit/09735cf940e754791bd4b599c88bbc236b9090b7) by techwithdunamix).
- fix: add TYPE_CHECKING import for improved type hinting in _builder.py ([8392fe9](https://github.com/nexios-labs/Nexios/commit/8392fe92fa5c51243c4ca9970fadf8134023724e) by techwithdunamix).

## [v2.7.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.7.0) - 2025-07-09

<small>[Compare with v2.6.2](https://github.com/nexios-labs/Nexios/compare/v2.6.2...v2.7.0)</small>

### Fixed

- fix: improve session handling and error logging ([f6fa900](https://github.com/nexios-labs/Nexios/commit/f6fa900799e1dc67b1ebe2d89e898e56d76cb6b0) by techwithdunamix).
- fix: add version bump test comment to main module ([bbebd50](https://github.com/nexios-labs/Nexios/commit/bbebd50382e3a9082b9d2399758f993441141e9a) by techwithdunamix).

## [v2.6.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.6.2) - 2025-07-04

<small>[Compare with v2.6.1](https://github.com/nexios-labs/Nexios/compare/v2.6.1...v2.6.2)</small>

## [v2.6.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.6.1) - 2025-07-03

<small>[Compare with v2.6.0](https://github.com/nexios-labs/Nexios/compare/v2.6.0...v2.6.1)</small>

## [v2.6.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.6.0) - 2025-06-30

<small>[Compare with v2.5.3](https://github.com/nexios-labs/Nexios/compare/v2.5.3...v2.6.0)</small>

### Removed

- remove: delete unused pytest configuration file ([59942ea](https://github.com/nexios-labs/Nexios/commit/59942ea62344665582aeb4ebcd0fee6d1022daf2) by techwithdunamix).

## [v2.5.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.5.3) - 2025-06-30

<small>[Compare with v2.5.2](https://github.com/nexios-labs/Nexios/compare/v2.5.2...v2.5.3)</small>

### Fixed

- fix: refine CORS preflight request test by updating allowed methods and headers to match middleware behavior ([be4dc12](https://github.com/nexios-labs/Nexios/commit/be4dc12626da31b71bb249c06fae2e0853f92b0d) by techwithdunamix).
- fix: update CORS middleware to handle preflight requests more robustly by refining header management and allowing dynamic header responses ([55ca14f](https://github.com/nexios-labs/Nexios/commit/55ca14f391e0da584b1a31075878d49b4e546f3e) by techwithdunamix).

## [v2.5.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.5.2) - 2025-06-29

<small>[Compare with v2.5.1](https://github.com/nexios-labs/Nexios/compare/v2.5.1...v2.5.2)</small>

### Fixed

- fix: correct spelling of 'exclude_from_schema' in application and routing modules ([98d2e24](https://github.com/nexios-labs/Nexios/commit/98d2e24bc1849dfcc60d7789278a7570a6793d6c) by techwithdunamix).
- fix: update header encoding in StreamingResponse for compatibility ([8cac5de](https://github.com/nexios-labs/Nexios/commit/8cac5de6390d8fba1dd54839396e4e1fedd5a51c) by techwithdunamix).
- fix: remove duplicate import of NexiosApp in day22 index documentation ([0ebdbb3](https://github.com/nexios-labs/Nexios/commit/0ebdbb36bacf8e6d58d5a1af14cd638dd1e214c2) by techwithdunamix).

## [v2.5.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.5.1) - 2025-06-26

<small>[Compare with v2.5.0](https://github.com/nexios-labs/Nexios/compare/v2.5.0...v2.5.1)</small>

### Fixed

- fix: correct indentation in release workflow for changelog generation step ([0fe3595](https://github.com/nexios-labs/Nexios/commit/0fe35957aab1d7f561958e9728430b84776e5023) by techwithdunamix).

## [v2.5.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.5.0) - 2025-06-21

<small>[Compare with v2.4.14](https://github.com/nexios-labs/Nexios/compare/v2.4.14...v2.5.0)</small>

### Fixed

- fix: allow optional status code in response methods and default to instance status code ([e4f1b15](https://github.com/nexios-labs/Nexios/commit/e4f1b15151304e65e914541ce2e46ce40324ad6c) by techwithdunamix).

## [v2.4.14](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.14) - 2025-06-20

<small>[Compare with v2.4.13](https://github.com/nexios-labs/Nexios/compare/v2.4.13...v2.4.14)</small>

### Fixed

- fix: handle directory initialization and path formatting in StaticFiles class for improved file serving, closes #136 ([13c9892](https://github.com/nexios-labs/Nexios/commit/13c98923d1a0d4532957943e1d4ddd78599c797e) by techwithdunamix).

## [v2.4.13](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.13) - 2025-06-18

<small>[Compare with v2.4.12](https://github.com/nexios-labs/Nexios/compare/v2.4.12...v2.4.13)</small>

### Fixed

- fix: update endpoint path formatting to simplify parameter representation in application.py ([617bd7b](https://github.com/nexios-labs/Nexios/commit/617bd7b6a03c9ff90a26eb49ac86f7e576e80a38) by techwithdunamix).
- fix: resolve merge conflict by removing unnecessary conflict markers in client.py ([2c6e1b2](https://github.com/nexios-labs/Nexios/commit/2c6e1b213cb1dae1c0704ba7c0b18d0e432a210e) by techwithdunamix).
- fix: reorder import statements for improved organization in structs.py ([a57c5cb](https://github.com/nexios-labs/Nexios/commit/a57c5cb656bbbc058fa79f723bb8adf27d1342ff) by techwithdunamix).

## [v2.4.12](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.12) - 2025-06-15

<small>[Compare with v2.4.11](https://github.com/nexios-labs/Nexios/compare/v2.4.11...v2.4.12)</small>

## [v2.4.11](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.11) - 2025-06-15

<small>[Compare with v2.4.10](https://github.com/nexios-labs/Nexios/compare/v2.4.10...v2.4.11)</small>

## [v2.4.10](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.10) - 2025-06-14

<small>[Compare with v2.4.9](https://github.com/nexios-labs/Nexios/compare/v2.4.9...v2.4.10)</small>

### Fixed

- fix: update GitHub Actions workflow to run Tox with uv ([c6c5a83](https://github.com/nexios-labs/Nexios/commit/c6c5a83721beec1482a9a6eb17919f126d29dcdd) by techwithdunamix).
- fix: address minor bugs in middleware handling and improve error logging for better debugging ([68e8055](https://github.com/nexios-labs/Nexios/commit/68e805567f9cfa4cabc8bb11c834250a67bbf221) by techwithdunamix).

## [v2.4.9](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.9) - 2025-06-06

<small>[Compare with v2.4.8](https://github.com/nexios-labs/Nexios/compare/v2.4.8...v2.4.9)</small>

## [v2.4.8](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.8) - 2025-06-05

<small>[Compare with v2.4.7](https://github.com/nexios-labs/Nexios/compare/v2.4.7...v2.4.8)</small>

### Fixed

- fix: restore __repr__ method in MakeConfig; add warning for missing secret_key in session handling ([49a6867](https://github.com/nexios-labs/Nexios/commit/49a6867f6f8104eea5a16243719a659e448f2a44) by techwithdunamix).
- fix(docs): improve clarity in concurrency guide and update examples for better understanding ([d790c96](https://github.com/nexios-labs/Nexios/commit/d790c967282b3bca49d550dc05c773f92c123cb9) by techwithdunamix).
- fix: correct import paths from 'cuncurrency' to 'concurrency' and remove deprecated concurrency utility file ([32863d9](https://github.com/nexios-labs/Nexios/commit/32863d9d882ade12ffd7c80289247c6c21f0d2d1) by techwithdunamix).
- fix(docs): update markdown configuration and correct file data handling in concurrency guide ([f3a85c2](https://github.com/nexios-labs/Nexios/commit/f3a85c24d9b49ae73aa97558f4f636448f49b9e3) by techwithdunamix).
- fix(docs): correct image upload handling in concurrency guide ([1e2230d](https://github.com/nexios-labs/Nexios/commit/1e2230db686e0f260398b26d0d0399cf629bc933) by techwithdunamix).

## [v2.4.7](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.7) - 2025-06-01

<small>[Compare with v2.4.6](https://github.com/nexios-labs/Nexios/compare/v2.4.6...v2.4.7)</small>

### Fixed

- fix(request): cast session to BaseSessionInterface for type safety ([3a462a3](https://github.com/nexios-labs/Nexios/commit/3a462a373de883f8533c13f68eb286f198c8bdc8) by techwithdunamix).
- fix(application): restore _setup_openapi call in handle_lifespan method ([076048f](https://github.com/nexios-labs/Nexios/commit/076048fdb9ee8554b852751f8bd9a1ef258e1918) by techwithdunamix).
- fix(session): streamline session configuration access and improve file path handling ([f963f3e](https://github.com/nexios-labs/Nexios/commit/f963f3e4a492776cd2e9b89ac4424ee2d3b5d718) by techwithdunamix).
- fix(session): improve session configuration handling with getattr for safer access ([9d48c3b](https://github.com/nexios-labs/Nexios/commit/9d48c3ba575c0d473e3e83681573fe8772a4d531) by techwithdunamix).
- fix(readme): update support icon URL to point to the new documentation site ([44c2d6a](https://github.com/nexios-labs/Nexios/commit/44c2d6a855b3982c52be2a9e5cfeeaeb2fbd6d99) by techwithdunamix).

## [v2.4.6](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.6) - 2025-05-30

<small>[Compare with v2.4.5](https://github.com/nexios-labs/Nexios/compare/v2.4.5...v2.4.6)</small>

### Fixed

- fix(openapi): implement OpenAPI setup during application shutdown and improve JSON property typing ([9fa250f](https://github.com/nexios-labs/Nexios/commit/9fa250fe159f2f1ed00d2445fa3f2bdd0fbaad63) by techwithdunamix).

## [v2.4.5](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.5) - 2025-05-27

<small>[Compare with v2.4.4](https://github.com/nexios-labs/Nexios/compare/v2.4.4...v2.4.5)</small>

### Fixed

- fix: Remove debug print statements and clean up lifespan event handling ([477fd63](https://github.com/nexios-labs/Nexios/commit/477fd6392ca831409398194fcfbfacc00243fcc5) by techwithdunamix).
- fix: Remove unnecessary method call in lifespan event handling ([9a90cef](https://github.com/nexios-labs/Nexios/commit/9a90cef6872bfcf0bc7bef2df5d90baf297d9cff) by techwithdunamix).
- fix: Improve error logging in lifespan event handling and clean up whitespace ([a7cb24c](https://github.com/nexios-labs/Nexios/commit/a7cb24cfad8219b48261839b2827220d4145f322) by techwithdunamix).

## [v2.4.4](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.4) - 2025-05-25

<small>[Compare with v2.4.3](https://github.com/nexios-labs/Nexios/compare/v2.4.3...v2.4.4)</small>

### Fixed

- fix: Set default path for Group initialization and add test for external ASGI app integration ([25e1a87](https://github.com/nexios-labs/Nexios/commit/25e1a8785698487c10543a08d90498dc50c44ebc) by dunamix).
- fix: Updates route handling to support both Routes and BaseRoute instances ([758808d](https://github.com/nexios-labs/Nexios/commit/758808deb533971d2377f5cc09e374b22b63a92e) by dunamix).
- fix: improve error message for client disconnection in ASGIRequestResponseBridge ([21ab8d7](https://github.com/nexios-labs/Nexios/commit/21ab8d7e3ad97bc5fa024bd430c09676f77bc6d7) by dunamix).

## [v2.4.3](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.3) - 2025-05-20

<small>[Compare with v2.4.2](https://github.com/nexios-labs/Nexios/compare/v2.4.2...v2.4.3)</small>

### Fixed

- fix: update workflow to ignore pushes to main branch ([196898d](https://github.com/nexios-labs/Nexios/commit/196898da56d693e91c76f9f8db91c70d3bc41538) by dunamix).
- fix: update typing SVG font and styling in README ([eba82f8](https://github.com/nexios-labs/Nexios/commit/eba82f89ca3ee5b95fc68870f295f2b5eb7032b7) by dunamix).
- fix: correct heading formatting in getting started guide ([88a2f9e](https://github.com/nexios-labs/Nexios/commit/88a2f9e4624fa4b810cb49c67fb9ba1f6955bec8) by dunamix).

## [v2.4.2](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.2) - 2025-05-15

<small>[Compare with v2.4.1](https://github.com/nexios-labs/Nexios/compare/v2.4.1...v2.4.2)</small>

### Added

- Add comprehensive WebSocket documentation including channels, consumers, events, and groups ([b3c109c](https://github.com/nexios-labs/Nexios/commit/b3c109cd19ddc3b84fb4cf164ae50a975cb36067) by dunamix).

### Fixed

- fix: improve JWT import error handling and raise informative exceptions ([3f4e386](https://github.com/nexios-labs/Nexios/commit/3f4e386b2c0c318693a1d75c1bbd19164b3bc50c) by dunamix).
- fix: update project description for clarity on performance features ([91acec4](https://github.com/nexios-labs/Nexios/commit/91acec4c4042a2faf9b89874d117b5b1a67aa80e) by dunamix).
- fix: clean up code formatting and add deprecation warning for get_application ([293f1ad](https://github.com/nexios-labs/Nexios/commit/293f1ad729fe23ef50f117e14b82ce05880db4a5) by dunamix).
- fix(ci): improve comments and update PyPI publishing step in release workflow ([d9375cd](https://github.com/nexios-labs/Nexios/commit/d9375cdbc3f8d97900d3cc1edb1fa6bc989620f4) by dunamix).

## [v2.4.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.1) - 2025-05-14

<small>[Compare with v2.4.0](https://github.com/nexios-labs/Nexios/compare/v2.4.0...v2.4.1)</small>

### Fixed

- fix(docs): remove redundant phrasing in framework description for clarity ([f50ab97](https://github.com/nexios-labs/Nexios/commit/f50ab9748246f7892a67ba5fc68dcdb5ea78aad4) by dunamix).
- fix(docs): simplify installation instructions by removing broken examples ([2d61ee4](https://github.com/nexios-labs/Nexios/commit/2d61ee4f58b936e1ee0e70c8b01002510752089d) by dunamix).
- fix(docs): correct GitHub link in VitePress config for accuracy ([acab1ba](https://github.com/nexios-labs/Nexios/commit/acab1ba6d1478e57f005c8136964aeec17f06d7d) by dunamix).
- fix(docs): update version badge from 2.4.0rc1 to 2.4.0 for consistency ([332d0d4](https://github.com/nexios-labs/Nexios/commit/332d0d4adb352d8a0e05ea7509760b5fa71a00b0) by dunamix).
- fix(docs): add template option to CLI usage instructions fix(docs): update CORS example to include proper configuration setup refactor(response): move remove_header method to improve clarity ([9731d85](https://github.com/nexios-labs/Nexios/commit/9731d85378b0c52e4582d9377e1e289356d08534) by dunamix).
- fix(router): inherit BaseRouter in Router and WSRouter classes for consistency ([f63a848](https://github.com/nexios-labs/Nexios/commit/f63a848abdb5de9d17ef4e805956b1ec1023974b) by dunamix).
- fix(docs): remove inline comment from routing example for clarity ([bcf1867](https://github.com/nexios-labs/Nexios/commit/bcf1867b3e4e8e892b2b01d18c88cdba2a3f46bd) by dunamix).
- fix(docs): remove inline comments from routing example for clarity ([6258d54](https://github.com/nexios-labs/Nexios/commit/6258d54ef8576ed7bc40c3bf2b3175a85838924d) by dunamix).
- fix: add type hints for version and callable parameters in multiple files ([563955e](https://github.com/nexios-labs/Nexios/commit/563955e2be8e06d5f7a750359c6603ebd2cb09bc) by dunamix).
- fix(router): remove debug print statement from Router class ([16f0708](https://github.com/nexios-labs/Nexios/commit/16f0708e03dadacc6361e1edb5f06fec8e2d9380) by dunamix).
- fix(router): store reference to the Router instance in scope for better access ([7538676](https://github.com/nexios-labs/Nexios/commit/7538676c30d39ed55a61b04f444dde8a433e9ba6) by dunamix).
- fix: update documentation URL to point to the correct Netlify site ([99d774f](https://github.com/nexios-labs/Nexios/commit/99d774f6eb72342d2fad89d67dc7a0c76a3d6d1f) by dunamix).
- fix(cli): update warning message for clarity on Granian integration ([19458f2](https://github.com/nexios-labs/Nexios/commit/19458f27bdf51afc30ee54b4fe87865a3d108b56) by dunamix).
- fix: update version number to 2.4.0 and enhance README for consistency ([673b3b5](https://github.com/nexios-labs/Nexios/commit/673b3b58bfb0cf2ca95593d443928526199626de) by dunamix).

## [v2.4.0](https://github.com/nexios-labs/Nexios/releases/tag/v2.4.0) - 2025-05-11

<small>[Compare with v2.3.1](https://github.com/nexios-labs/Nexios/compare/v2.3.1...v2.4.0)</small>

### Added

- Add WebSocket support and documentation updates ([2426e63](https://github.com/nexios-labs/Nexios/commit/2426e63e65e0fffc5098d39e1ed85d15cf542fd8) by dunamix).

### Fixed

- fix: update feature list in README for accuracy and clarity ([eedeb24](https://github.com/nexios-labs/Nexios/commit/eedeb24f8ed895bd3628f4c3a9f20d5db74620a1) by dunamix).
- fix: update version number and enhance README badges ([13c099a](https://github.com/nexios-labs/Nexios/commit/13c099ae925003f3953ab47168294b8166724113) by dunamix).
- fix: remove redundant options and examples from CLI documentation ([a24f986](https://github.com/nexios-labs/Nexios/commit/a24f986f1e11e5c3c2bfcb71355677862e45e282) by dunamix).
- fix: remove base path from VitePress configuration ([8b3092e](https://github.com/nexios-labs/Nexios/commit/8b3092eb4064c4b5890be76cd4276f56916a90c5) by dunamix).
- fix: update base path in VitePress configuration ([a7cea7f](https://github.com/nexios-labs/Nexios/commit/a7cea7f23565c3710cd2d0905046a2b60202572b) by dunamix).
- fix: set base path in VitePress configuration ([681a9c4](https://github.com/nexios-labs/Nexios/commit/681a9c4554d189f9fcd9acbb9c8ac4f18a8d5db5) by dunamix).
- fix: update install command to prevent frozen lockfile during dependency installation ([d932457](https://github.com/nexios-labs/Nexios/commit/d932457d25f3084f558eeb43cda6130a4c014e15) by dunamix).
- fix: correct whitespace in hero name in index.md ([8a27f9e](https://github.com/nexios-labs/Nexios/commit/8a27f9ecb6c086016afeb0c6fa1a405099ce06c6) by dunamix).
- fix: update install command in GitHub Actions workflow for consistency ([c39f1d9](https://github.com/nexios-labs/Nexios/commit/c39f1d99e9185af6ec2d266e8605a3248885ff76) by dunamix).
- fix: update step name for clarity in GitHub Pages deployment ([cb13f80](https://github.com/nexios-labs/Nexios/commit/cb13f8045f38d765b9f1136f31c5dedd893cd0d5) by dunamix).
- fix: remove .nojekyll creation step from deploy workflow ([43c419e](https://github.com/nexios-labs/Nexios/commit/43c419ea00085efae93724a5764ac655fd7d5fbf) by dunamix).
- fix: update install command in deploy-docs workflow to use pnpm install ([66ab0d9](https://github.com/nexios-labs/Nexios/commit/66ab0d9878c50a3f39996635d78f0f60f797e43a) by dunamix).
- fix: enable pnpm setup and correct build command formatting in deploy-docs workflow ([d931e15](https://github.com/nexios-labs/Nexios/commit/d931e15836f9639d4f27b836dafe53393bfc833b) by dunamix).
- fix(docs): update metadata and lockfile for improved dependency management ([2cadb3c](https://github.com/nexios-labs/Nexios/commit/2cadb3c23e7d471b934554f43a1c9a0730511f10) by dunamix).
- fix(app): correct HTTP request handling in NexiosApp class docs(guide): update installation and routing documentation for clarity ([863b120](https://github.com/nexios-labs/Nexios/commit/863b120005fecf32fe39a5ff7eff2f2ed9c84693) by dunamix).
- fix(docs): correct path parameter access in room handler and chat endpoint ([ac4c0c1](https://github.com/nexios-labs/Nexios/commit/ac4c0c11c179763310722e1439a65dea6cdc5dd7) by dunamix).
- fix(config): Initialize configuration in NexiosApp constructor ([3e89ae6](https://github.com/nexios-labs/Nexios/commit/3e89ae6330ed491d332e8e232cef7e9cfc09e53e) by dunamix).
- fix: Correct order of sections in SUMMARY.md for better clarity ([124a354](https://github.com/nexios-labs/Nexios/commit/124a3543ae661fae379ac2a96fed1cf1506ba1f6) by dunamix).
- fix(openapi): set default type for Schema and update model references ([e546910](https://github.com/nexios-labs/Nexios/commit/e5469107d19d6caf2183d4ea47f1fe8c50d21b84) by dunamix).
- fix(static): improve directory handling and validation in StaticFilesHandler fix(structs): add default value support to RouteParam.get method ([b6cef3d](https://github.com/nexios-labs/Nexios/commit/b6cef3deb1e79093f5e9163c344d9608676b9478) by dunamix).
- fix(import): handle ImportError for Jinja2 with a clear installation message ([b7dd792](https://github.com/nexios-labs/Nexios/commit/b7dd7924f92ff532c0e90f87be620828e61de596) by dunamix).
- fix(routing): remove unused response_model parameter and handle empty path case ([b43df18](https://github.com/nexios-labs/Nexios/commit/b43df185336237ecf8aef08ec615df436de1ccf9) by dunamix).
- fix(application): set default config if none provided and clean up type ignores fix(exception_handler): refine exception handler type annotations refactor(formparsers): remove unnecessary type ignores and improve readability refactor(request): simplify Request class definition refactor(routing): enhance type annotations and clean up type ignores fix(types): correct response type alias for consistency ([39c062a](https://github.com/nexios-labs/Nexios/commit/39c062a70eea8686edea684083d0ab57a505016c) by dunamix).

### Removed

- Remove legacy documentation files for static files, templating, Tortoise ORM, WebSockets, and general Nexios overview to streamline the project and focus on updated content. ([0ea37f5](https://github.com/nexios-labs/Nexios/commit/0ea37f5530be0602ec71d26d5979ce4df3726ceb) by dunamix).

## [v2.3.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.3.1) - 2025-04-14

<small>[Compare with v2.3.0-rc.1](https://github.com/nexios-labs/Nexios/compare/v2.3.0-rc.1...v2.3.1)</small>

### Fixed

- fix(application): update default config import and streamline code formatting ([8cec770](https://github.com/nexios-labs/Nexios/commit/8cec77035420dc38073c7a9e4cd3bbf087da26ad) by dunamix).
- fix(auth): remove unused import from jwt backend ([512a764](https://github.com/nexios-labs/Nexios/commit/512a764a83a8066410dc472c6df8fe81a87ec8cb) by dunamix).
- fix(docs): improve formatting and clarity in managing_config.md ([369346c](https://github.com/nexios-labs/Nexios/commit/369346cd4b1c014a202b82e7b932715bcd2d8b39) by dunamix).
- fix(docs): standardize warning formatting and update hook descriptions in misc.md ([0438641](https://github.com/nexios-labs/Nexios/commit/04386418a1e1f53b5c8110c81c1ba63dff3c448a) by dunamix).
- fix(docs): add missing links for Managing Config and Misc in SUMMARY.md ([80993b8](https://github.com/nexios-labs/Nexios/commit/80993b837c85680c48f5fb0ee8c23600f59da70c) by dunamix).
- fix(readme): update badge alignment and formatting in README files ([7aac3c7](https://github.com/nexios-labs/Nexios/commit/7aac3c73dc31a5ec2c2273509c2138aa774125aa) by dunamix).
- fix(funding): add GitHub funding link for techwithdunamix ([9c482cd](https://github.com/nexios-labs/Nexios/commit/9c482cdc25b7e68b3cec450cf70cf73d35cb35bb) by dunamix).
- fix(tox): add pytest-asyncio and pydantic dependencies; update asyncio_fixture_scope in pytest options ([8a004e1](https://github.com/nexios-labs/Nexios/commit/8a004e134b59767333e43c8b6bb70b7511eae289) by dunamix).
- fix(readme): update image attributes for Swagger API documentation ([399d77f](https://github.com/nexios-labs/Nexios/commit/399d77fac6bd1a8452adc66844c3901b604d74b3) by dunamix).
- fix(readme): update visitor count alt text and correct image path ([4bd1fd0](https://github.com/nexios-labs/Nexios/commit/4bd1fd026e366410877f52e9c79a0004a0dc8e64) by dunamix).
- fix(docs): update GzipMiddleware usage in example to use wrap_asgi method ([8fa590b](https://github.com/nexios-labs/Nexios/commit/8fa590b3758e316c4c5c1ae985efc4346d547727) by dunamix).
- fix(router): handle empty context in render function to prevent errors ([ebdc3de](https://github.com/nexios-labs/Nexios/commit/ebdc3de17c7027a3e59a67da0a4c4732161b4fb9) by dunamix).
- fix(router): correct path handling in FileRouter for improved route mapping ([d0a2c9d](https://github.com/nexios-labs/Nexios/commit/d0a2c9db279b8b940e65b49bda99d8c96c73beda) by dunamix).
- fix(router): improve method handling in FileRouter for route mapping ([d09106f](https://github.com/nexios-labs/Nexios/commit/d09106f346a1874a40fe209e587245c944f5a3c5) by dunamix).
- fix(router): fixed method handling and schema exclusion in FileRouter ([a44f1ec](https://github.com/nexios-labs/Nexios/commit/a44f1ecc72b67ad83256f16c0d12a9a1fa8d741e) by dunamix).

## [v2.3.0-rc.1](https://github.com/nexios-labs/Nexios/releases/tag/v2.3.0-rc.1) - 2025-04-04

<small>[Compare with first commit](https://github.com/nexios-labs/Nexios/compare/921f570f769df8d1935e7251ef985a69fb2fc537...v2.3.0-rc.1)</small>

### Added

- added new changed ([9af76fc](https://github.com/nexios-labs/Nexios/commit/9af76fc6aa3b77630984d7eac97ccf0e8793d763) by dunamix).
- added local file management ([ee7aa9a](https://github.com/nexios-labs/Nexios/commit/ee7aa9ad734ed1bea20f42b53f4e94164ee62001) by dunamix).
- added custom validator ([b696e2b](https://github.com/nexios-labs/Nexios/commit/b696e2b6eb7cb5cb2d2d3b70add941f287c12326) by dunamix).
- added asgiref to installment dependecies ([e68b722](https://github.com/nexios-labs/Nexios/commit/e68b722617dd864ca85baaf2948995c4f23f79ba) by dunamix).
- added setup ([dac09cb](https://github.com/nexios-labs/Nexios/commit/dac09cbea5af0e48db77fa313b8e75bab5d5e12b) by dunamix).
- addeed cusom validation ([9bd8212](https://github.com/nexios-labs/Nexios/commit/9bd821291dde18d33c31b5177223e8eaa1394568) by dunamix).
- added validation ([c2d066c](https://github.com/nexios-labs/Nexios/commit/c2d066cdd16a15564493c5e93281cd6a77ef2d2b) by dunamix).
- add custom validator options ([2684111](https://github.com/nexios-labs/Nexios/commit/2684111cd7b72c11d7e91e765c712420d3910e25) by dunamix).
- added formdata ([e5b764f](https://github.com/nexios-labs/Nexios/commit/e5b764f337adc7ae7ef0baaccc92940970b66059) by dunamix).

### Fixed

- fix(routing): remove unnecessary blank line in Router class ([0b04c40](https://github.com/nexios-labs/Nexios/commit/0b04c400a72c7dfe27726333a6d48449b5322f03) by dunamix).
- fix(cors): standardize header casing and improve CORS middleware logic ([cb02735](https://github.com/nexios-labs/Nexios/commit/cb027352c0ce75bbe32f45258ae7ba2bbdec415c) by dunamix).
- fix(session): correct string representation in BaseSessionInterface and clean up test cases ([7d74cbf](https://github.com/nexios-labs/Nexios/commit/7d74cbf7e034a9e355108b200602090d54904ebb) by dunamix).
- fix(session): update session expiration logic and improve session management ([c50b14b](https://github.com/nexios-labs/Nexios/commit/c50b14b3ffdd2fc097a132b2b4040fdb32e59499) by dunamix).
- fix(test): correct typo in first_middleware function parameter name ([b3bf139](https://github.com/nexios-labs/Nexios/commit/b3bf139fa0863ae05792efb674de68b55ede0a57) by dunamix).
- fix(workflow): update permissions and simplify git push in format-code.yml ([1e478bc](https://github.com/nexios-labs/Nexios/commit/1e478bc85e2c134551cce3985f87f2e08ed8a3b3) by dunamix).
- fix(workflow): update GitHub token usage in format-code.yml for secure pushing ([129b7d4](https://github.com/nexios-labs/Nexios/commit/129b7d47df67a261dd523f33979e42cd540e762f) by dunamix).
- fix(workflow): update GitHub token secret name in deploy-docs.yml ([fb60e22](https://github.com/nexios-labs/Nexios/commit/fb60e223d534efd6231a260dc1488f6a2183b647) by dunamix).
- fix(websockets): remove unused import of MiddlewareType in consumers.py ([288bff7](https://github.com/nexios-labs/Nexios/commit/288bff7998129d003c961e9f03258e15f601397e) by dunamix).
- fix(websockets): import WebsocketRoutes inside as_route method to avoid import errors ([9182134](https://github.com/nexios-labs/Nexios/commit/9182134cf5ad0ef6090db8ba1cc2a871b5da7f2e) by dunamix).
- fix: 🔧: correct app reference in handle_http_request; add wrap_with_middleware method to support ASGI middleware integration; improve error handling in BaseMiddleware ([bcaa3ee](https://github.com/nexios-labs/Nexios/commit/bcaa3eea3ef1c432ee424e232916590cf9ca877e) by dunamix).
- fix: 🔧: suppress RuntimeError in BaseMiddleware to handle EndOfStream gracefully; add type ignore for message assertion ([a14e73b](https://github.com/nexios-labs/Nexios/commit/a14e73bcfccb9d2a71614ac889b9a9b7b27c7054) by dunamix).
- fix: 🔧: remove debug print statement for message in NexiosApp to clean up output ([0a9dd94](https://github.com/nexios-labs/Nexios/commit/0a9dd9439d986c73af0b22e3e8adf8d2674b844f) by dunamix).
- fix: 🔧: improve exception handling in collapse_excgroups; update BaseResponse initialization to remove setup parameter and enhance cookie management ([ae2e1b4](https://github.com/nexios-labs/Nexios/commit/ae2e1b41a13b44b0b5d51995773f1bfbfdfa325e) by dunamix).
- fix: 🔧: update datetime import to use timezone.utc; simplify payload sending logic in Channel class ([74440f4](https://github.com/nexios-labs/Nexios/commit/74440f46e219a5a009e39edffe0085d5597c935a) by dunamix).
- fix: 🔧: handle empty range end in FileResponse initialization to prevent ValueError ([0b846b5](https://github.com/nexios-labs/Nexios/commit/0b846b584d860eaa39263df1f389415925f6f0af) by dunamix).
- fix: 🔧: update FileResponse initialization and improve range handling in response.py; modify BaseMiddleware to suppress RuntimeError; clean up test_response.py ([22f4374](https://github.com/nexios-labs/Nexios/commit/22f43743cec74710ee2ac9fefe96479eb8ffeb16) by dunamix).
- fix: 🔧: update FileResponse initialization to include setup parameter and clean up range handling comments ([02a5196](https://github.com/nexios-labs/Nexios/commit/02a51961730471b0b29bde008594f3d409fea42e) by dunamix).
- fix: 🔧: update .gitignore, improve gzip documentation, refactor middleware handling, and replace print statements with logger in hooks ([feaa074](https://github.com/nexios-labs/Nexios/commit/feaa0747c27e6e74e32eb8eec502d8d175bb589b) by dunamix).
- fix: 🔧: ensure websocket is closed properly on disconnect in WebSocketEndpoint ([1bd2372](https://github.com/nexios-labs/Nexios/commit/1bd23724acb270b1d4953e7a40c59136b7952540) by dunamix).
- fix: 🔧: add channel_remove_status variable in ChannelBox and simplify loop in WebSocketEndpoint ([f00c6c4](https://github.com/nexios-labs/Nexios/commit/f00c6c4eed94885f08c751ca90b6fe9a950a1ddc) by dunamix).
- fix: 🔧: make expires parameter optional in Channel class constructor ([58dc8ed](https://github.com/nexios-labs/Nexios/commit/58dc8ed592c2f1929138d79b8ab249fd1ddd5688) by dunamix).
- fix: 🐛 fix: enhance exception handling by raising exceptions when no handler is present; add user setter to Request class ([caeb648](https://github.com/nexios-labs/Nexios/commit/caeb64846606cda970f23063949e35f7a538ac53) by dunamix).
- fix: simplify method type casting in Request class ([9ea14e5](https://github.com/nexios-labs/Nexios/commit/9ea14e560894cb0ea138b264f10c4abbbcdc5068) by dunamix).
- fix: update cookie deletion logic to use None and set expiry to 0 ([6e24d61](https://github.com/nexios-labs/Nexios/commit/6e24d61c07b70a1597d0106b241b49e7932b43e2) by dunamix).
- fix: improve request handling and error logging in NexioApp ([f96d209](https://github.com/nexios-labs/Nexios/commit/f96d209addf6c9403fbaeaaafbfdf09d1ff7a2b8) by dunamix).
- fix: update allowed HTTP methods to lowercase and improve method validation in CORS middleware ([c0eb15d](https://github.com/nexios-labs/Nexios/commit/c0eb15daa61202219958c6a534dcba55da220de2) by dunamix).
- fix: remove debug print statements from response and middleware classes ([40d65f6](https://github.com/nexios-labs/Nexios/commit/40d65f66c14799bfb2f8945c905e86bc95719b58) by dunamix).
- fix: remove debug print statements and update CORS headers handling ([3154d2c](https://github.com/nexios-labs/Nexios/commit/3154d2c0388e548aa49d9ebd25baf4b2e42340ff) by dunamix).
- fix : fixed more issues with ws ([0d56016](https://github.com/nexios-labs/Nexios/commit/0d56016f955caa3e256823cb80864601e6bd88e0) by dunamix).
- fix : adjusted staic hadnler ([3090371](https://github.com/nexios-labs/Nexios/commit/3090371547b44035948e64f6f1a7cebf0fb27128) by dunamix).
- fix : returning 404 in a loop ([a0e2f19](https://github.com/nexios-labs/Nexios/commit/a0e2f19c212717b5f64a538876a7660e4ef398d4) by dunamix).
- fix : fix issues with middleware returning None ([c96740e](https://github.com/nexios-labs/Nexios/commit/c96740e52395e847ddfb3034ed7b230b1867640f) by dunamix).
- fix : fix  issue with cors ([a42c2bf](https://github.com/nexios-labs/Nexios/commit/a42c2bfe249390b1a0131c749b117e8a3c250ccb) by dunamix).
- fix : fixing issues with pre routing middlewares ([168ce29](https://github.com/nexios-labs/Nexios/commit/168ce29c97e76e0352f5a0e5985bb009eee23c49) by dunamix).
- fixed issue ([a021fa8](https://github.com/nexios-labs/Nexios/commit/a021fa84d985230a54967e00b547bd980d17218a) by dunamix).
- fix : fixed cors error ([8c8da03](https://github.com/nexios-labs/Nexios/commit/8c8da033795eb4bac6dffd47cf0f9d4c07347d35) by dunamix).
- fix : issue with cors cors errors ([9b6a3d8](https://github.com/nexios-labs/Nexios/commit/9b6a3d849118ca957155b26c1e0abc68975a24d7) by dunamix).
- fix : fixed issue with form data ([e8f4910](https://github.com/nexios-labs/Nexios/commit/e8f4910c8c945ca9bde05fcce563e8d7d43d47ec) by dunamix).
- fix : fixed issues witj cookies ([6427145](https://github.com/nexios-labs/Nexios/commit/642714571ef9fcdcd347929ae1df36c453e215c4) by dunamix).
- fix error with cors error ([b674bf8](https://github.com/nexios-labs/Nexios/commit/b674bf88fa99bbf2aba31723f9b84d9799ac97e2) by dunamix).
- fix : cors issues on status not equal to 200 ([04af599](https://github.com/nexios-labs/Nexios/commit/04af599ebfc9d43f300c5d7afb27fb2dce67eb96) by dunamix).
- fix : fixed issues with cors ([122fbd9](https://github.com/nexios-labs/Nexios/commit/122fbd926029a3f26e6c1ca0e423d0b073d76cd7) by dunamix).
- fix : trying to fix cors errors ([0b0994e](https://github.com/nexios-labs/Nexios/commit/0b0994e0f6f48035258aa5f99c152a00bfab2bf8) by dunamix).
- fix : fiexed issue with validator ([076ef31](https://github.com/nexios-labs/Nexios/commit/076ef31ded0ec94d3c44f84ddf08e87b2bc78216) by dunamix).
- fix : error with middleware stack ([d0ca0e6](https://github.com/nexios-labs/Nexios/commit/d0ca0e68c878bcec0e2917f0912a9757a2549648) by dunamix).
- fix : fix issue with cookie parser ([db55269](https://github.com/nexios-labs/Nexios/commit/db552691063793b5590aca19c73f13fec4e1d4c6) by dunamix).
- fixed : issues with validation ([fae885b](https://github.com/nexios-labs/Nexios/commit/fae885b2f44fb3662e3ef13c4515b4d87451a260) by dunamix).
- fix : make some changes to the session ([8765b2a](https://github.com/nexios-labs/Nexios/commit/8765b2afcf4bb6e5520fcd79a7bf9440427fbf37) by dunamix).
- fix : fixed issues issues  with shared value amongs schema instance ([1a066f0](https://github.com/nexios-labs/Nexios/commit/1a066f098a556f5f27647c41e796b26320463aa6) by dunamix).
- fix : fix validators ([db756f3](https://github.com/nexios-labs/Nexios/commit/db756f339c584f876d94addac3aa6be0291dfb32) by dunamix).
- fix : some new issues ([a97606a](https://github.com/nexios-labs/Nexios/commit/a97606ab5f87f303c0321c9df650d79aa370b355) by dunamix).
- fix : made some new fix to enable ease websocket feature development ([615136d](https://github.com/nexios-labs/Nexios/commit/615136d4620aff51de71aeeb2f34eec7c34707c7) by dunamix).
- fix : fix url params error ([468e873](https://github.com/nexios-labs/Nexios/commit/468e873eec5a55a71f26945bfbe7613a777a8aa6) by dunamix).
- fix : changed name to nexios ([0341234](https://github.com/nexios-labs/Nexios/commit/03412348599849425220b0c32bd9b85f3f309cef) by dunamix).
- fix: re issues ([94803fe](https://github.com/nexios-labs/Nexios/commit/94803feae27e8785109c8e94ed798616364b37cd) by dunamix).
- fix :updated routes logic ([81d51c0](https://github.com/nexios-labs/Nexios/commit/81d51c05bc494716b6d6c903a6f5e00479798002) by dunamix).
- fix : route issue ([68e25bc](https://github.com/nexios-labs/Nexios/commit/68e25bc5ae5728d244c1c9379b8db5d853e2a3c8) by dunamix).
- fix event loop issue ([3571a36](https://github.com/nexios-labs/Nexios/commit/3571a36e17dff19ea2a42664067d1a39372d54c8) by dunamix).
- fix : fix few issues from the request object ([0bfc97a](https://github.com/nexios-labs/Nexios/commit/0bfc97abcfe849c9f3459394a732fa13b7229c83) by dunamix).
- fix :rewrote the response cookire stratagy ([2a98360](https://github.com/nexios-labs/Nexios/commit/2a98360464a140f6950dcad3d468ccd2733fd5e9) by dunamix).
- fixed few issues with middelware ([5797621](https://github.com/nexios-labs/Nexios/commit/579762116884963e434fc38619144ac732bc735d) by dunamix).

### Changed

- changes ([5cf3a6a](https://github.com/nexios-labs/Nexios/commit/5cf3a6a2cff981bc7181c45ca40894a20cc80648) by dunamix).
- changes to session ([2859066](https://github.com/nexios-labs/Nexios/commit/28590669abd90eb0355ba257e3c5fa66750de980) by dunamix).

### Removed

- removed unused code ([4e565f1](https://github.com/nexios-labs/Nexios/commit/4e565f14011854408b5d10c4bd40fc83d4522476) by dunamix).

