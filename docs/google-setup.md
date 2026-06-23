# Google credentials setup

This guide covers creating a Google Cloud service account and granting it access to your GSC properties and GA4. It takes about 10 minutes.

**Why a service account?** OAuth credentials work fine for personal use, but Claude Desktop has no browser to run the OAuth flow. A service account JSON gives the server a stable, non-interactive credential that works everywhere. See [OAuth option](#option-b-oauth-for-personal-use) if you prefer to authenticate interactively.

---

## Option A: Service account (recommended)

### Step 1: Create or select a Google Cloud project

Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (or use an existing one). The project name is arbitrary; `gsc-mcp` works fine.

### Step 2: Enable the required APIs

In the left sidebar, go to **APIs & Services > Library** and enable these three APIs one by one:

| API name | Required for |
|---|---|
| **Google Search Console API** | All GSC analytics, inspection, and sitemap tools |
| **Web Search Indexing API** | `submit_url`, `submit_batch` |
| **Google Analytics Data API** | All `ga4_*` tools and `traffic_health_check`, `page_analysis` |

If you only plan to use GSC tools (no GA4, no indexing), enabling only the first two is enough.

### Step 3: Create a service account

Go to **IAM & Admin > Service Accounts**, then click **Create Service Account**.

- Name: anything descriptive, e.g. `gsc-mcp`
- Service account ID: auto-filled from the name
- Description: optional

Click **Done**. No project-level IAM role is needed for this account (GSC and GA4 access is granted per-property later).

### Step 4: Download the JSON key

Click the service account you just created, go to the **Keys** tab, click **Add Key > Create new key**, and select **JSON**. A file downloads automatically: keep it somewhere safe (e.g. `~/.config/gsc-mcp/service-account.json`).

This JSON contains the `client_email` field, which is the address you will use to grant access in GSC and GA4.

---

### Step 5: Add the service account to Google Search Console

This is the step most guides skip. **The APIs alone are not enough.** The service account must be added as a user on each property in GSC.

Go to [Google Search Console](https://search.google.com/search-console), select your property, then go to **Settings > Users and permissions > Add user**.

Enter the `client_email` from your JSON file (it looks like `gsc-mcp@your-project.iam.gserviceaccount.com`).

**Choose the right permission level:**

| Permission | Analytics and inspection tools | Indexing API (`submit_url`, `submit_batch`) |
|---|---|---|
| **Owner** | Yes | Yes |
| **Full** | Yes | No |
| **Restricted** | No | No |

If you want to use `submit_url` or `submit_batch`, the service account must be an **Owner**. The Indexing API rejects requests from accounts with only Full access.

Repeat this for each GSC property you want to query. The server can only access properties where the service account has been explicitly added.

#### Domain properties vs URL prefix properties

GSC has two property types:

**URL prefix** (`https://example.com/`): the service account can be added as Owner directly through the Settings UI.

**Domain property** (`sc-domain:example.com`): ownership in a domain property is tied to DNS verification. You can add the service account as a Full user through the UI, but you cannot make it an Owner this way. To use the Indexing API with a domain property, the service account must be granted delegated ownership. The simplest path is to create a URL prefix property for the same domain and add the SA as Owner there; it will have the same data.

### Step 6: Add the service account to GA4 (optional)

Skip this step if you are not using the `ga4_*` tools.

Go to your GA4 property, then **Admin > Property Access Management** and click the **+** button to add a user. Enter the `client_email` and select the **Viewer** role.

Set the `GA4_PROPERTY_ID` environment variable to your numeric property ID, visible in GA4 **Admin > Property Settings** (e.g. `123456789`). The `properties/` prefix is added automatically.

---

### Step 7: Configure the environment

Set these variables before running the server:

```bash
# Required for GSC and Indexing API
export GSC_SERVICE_ACCOUNT_PATH=/absolute/path/to/service-account.json
export GSC_SKIP_OAUTH=true

# Required only if you use GA4 tools
export GA4_PROPERTY_ID=123456789
```

Or use `.env` (see `.env.example`):

```bash
cp .env.example .env
# Edit .env with your values
```

**Note:** `GSC_SKIP_OAUTH=true` prevents the server from falling back to the browser OAuth flow when the SA credentials are missing. Omit it if you want OAuth as a fallback.

---

### Step 8: Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "gsc-mcp": {
      "command": "uvx",
      "args": ["gsc-mcp"],
      "env": {
        "GSC_SERVICE_ACCOUNT_PATH": "/absolute/path/to/service-account.json",
        "GSC_SKIP_OAUTH": "true",
        "GA4_PROPERTY_ID": "123456789"
      }
    }
  }
}
```

Remove the `GA4_PROPERTY_ID` line if you are not using GA4 tools.

After saving, restart Claude Desktop. The `gsc-mcp` server should appear in the tools panel.

---

## Option B: OAuth (for personal use)

OAuth is simpler to set up but requires a browser for the first authentication, so it does not work in Claude Desktop out of the box.

In the Google Cloud Console, go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**. Select **Desktop app** as the application type. Download the resulting JSON file.

```bash
export GSC_CREDENTIALS_PATH=/path/to/oauth-client-secret.json
gsc-mcp
```

The first run opens a browser tab for Google login. After you authorize, the token is saved locally (in `~/Library/Application Support/gsc-mcp/` on macOS) and reused on subsequent runs. No browser needed after the initial flow.

OAuth grants access to all GSC properties your Google account can see, so no manual per-property setup is needed.

**Note on the Indexing API with OAuth:** even with OAuth, the authenticated account must be a property owner in GSC to use `submit_url` and `submit_batch`.

---

## Quotas and limits

| API | Default daily limit | Notes |
|---|---|---|
| Search Console API | 25,000 queries | Per project |
| Indexing API | 200 requests | Per project; gsc-mcp tracks usage in memory and warns at 180 |
| GA4 Data API | 25,000 tokens | Per property per day |

The Indexing API daily limit resets at midnight Pacific Time. The in-memory counter resets on server restart. Restarting mid-day after submitting URLs means the count resets and you may exceed the daily limit without knowing.

---

## Troubleshooting

**"403 Forbidden" on GSC tools**: the service account email has not been added to the property, or it has been added with Restricted access. Check Settings > Users and permissions in GSC.

**"403 Forbidden" on `submit_url` / `submit_batch`**: the service account has Full access but not Owner access. Go to Settings > Users and permissions and change the permission level to Owner.

**"RuntimeError: No GA4 config"**: `GA4_PROPERTY_ID` is not set. Add it to your env or to the `env` block in `claude_desktop_config.json`.

**"RuntimeError: No credentials"**: `GSC_SERVICE_ACCOUNT_PATH` is not set or the file does not exist at the specified path. Check that the path is absolute (not `~`-expanded, since MCP servers may not expand tildes).

**Domain property + Indexing API**: service accounts cannot be set as Owners on domain properties through the GSC UI. Create a URL prefix property for the same site and add the SA as Owner there.
