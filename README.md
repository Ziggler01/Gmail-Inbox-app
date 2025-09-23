Gmail Inbox Scanner is a utility to Scan the gmail inbox and idenitify the number of emails and provide a  form to the user to keep/unsubscribe/delete emails based on the action by the user.
Phase 1 - Phase 1 was essentially about authentication + data fetch + first level aggregation + basic display

Core Concepts Used

OAuth 2.0 Authentication
  Google Identity → OAuth client (client_id, client_secret, redirect_uri)
  Token exchange (auth code → access token & refresh token)
  Secure callback handling
Google Gmail API (Read-only scope)
  gmail.readonly scope for safe access
  Fetching user messages metadata (messages.list, messages.get)
  Extracting headers (From, Subject, Date)
FastAPI Backend
  REST endpoints (/oauth/callback, /jobs/scan, etc.)
  Async request handling
  JSON responses
Data Processing
 Parsing email headers (From → sender, message counts)
 Aggregating senders and message counts
 Generating “Top senders” list
UI/UX Layer

 Frontend polling /jobs/scan → showed “Loading” → then results
 Displaying statistics (counts, charts/lists)
 Version Control & Collaboration
GitHub repo setup (git push, git pull --rebase)
 Merging remote changes before committing new ones
 Error Handling / Debugging
Handling 500 errors during callback
 Fixing FastAPI endpoint mapping (/jobs/scan)
 Logging for debugging token/code issues
 ![CI](https://github.com/Ziggler01/Gmail-Inbox-app/actions/workflows/ci.yml/badge.svg)

📂 Outputs from Phase 1
  OAuth flow working (user can sign in and grant access)
  Message scanning job (/jobs/scan) retrieving Gmail data
  Processed results: sender/message counts, top senders list
  Basic UI feedback: “Loading…” → replaced by actual counts
