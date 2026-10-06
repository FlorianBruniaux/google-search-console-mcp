# Evidence and safety

Search Console MCP keeps provider semantics and evidence states explicit. Use these boundaries before turning a result into a recommendation or a write action.

<figure class="docs-visual">
  <img src="/images/docs/guarded-action-loop.webp" width="1376" height="768" alt="An assistant inspects evidence, compares sources, explains uncertainty, and passes one action through a confirmation gate." loading="lazy">
  <figcaption>The loop returns to observation. Confirmation permits one bounded request, not unrestricted automation.</figcaption>
</figure>

## Evidence states

- **Observed:** an API response or fetched public-page value returned for the stated target and window.
- **Derived:** a calculation based on observed values, with its input window and method attached.
- **Requested:** a provider accepted a submission request.
- **Crawled:** the provider later reports a fetch or crawl event.
- **Indexed:** the provider later reports the URL in its searchable index.

Requested, crawled, and indexed are different states. A successful submission is never reported as proof of indexation.

## Provider boundaries

Google and Bing expose different metrics, scopes, delays, and position semantics. Compare directional evidence, not superficially similar field names. Keep the provider and observed window attached to every conclusion.

## Guarded actions

Read tools can inspect verified properties and public pages. Write tools require an explicit target and bounded action. Before submitting anything, confirm the provider, site, URL set, action, and expected blast radius.

<ol class="guarded-flow">
  <li><strong>Read</strong><span>Collect provider responses and public-page facts.</span></li>
  <li><strong>Compare</strong><span>Keep provider semantics and observed windows separate.</span></li>
  <li><strong>Explain</strong><span>Expose limits, derived values, and remaining uncertainty.</span></li>
  <li><strong>Confirm</strong><span>Name one provider, target, action, and blast radius.</span></li>
  <li><strong>Submit</strong><span>Record the response, then measure later states separately.</span></li>
</ol>

## Secrets

Keep credentials in the MCP server environment or the client configuration. Do not paste service-account JSON, OAuth tokens, Bing API keys, or IndexNow keys into prompts or public issue reports.

Continue with the [installation guide](/docs/installation/) or run a [quick audit](/docs/examples/quick-audit/).
