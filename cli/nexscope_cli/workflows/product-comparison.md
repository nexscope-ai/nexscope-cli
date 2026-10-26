# Product comparison in a supported agent

Use the installed CLI's `workflow compare` implementation as the single execution
rule source. Read its actual `--help` and `capabilities describe` contract; do not
reimplement collection, budget accounting or evidence validation in the host.

For a request to compare products, reuse the user's supplied market, identifiers,
keyword, file, output location, authentication context and existing authorization.
Ask only for missing information or an actual scope expansion.

- For a user CSV/JSON, use `report compare` locally. Do not connect an account,
  read keyring, upload the file or refresh remote data. The live ASIN limit does
  not apply to local rows. Offer HTML, CSV and Markdown; return the actual paths.
- For supplied ASINs, prepare `workflow compare --asins ... --dry-run` and inspect
  its exact request budget and unknown costs. Skip search. In the approved scope,
  execute once using `--execute --allow-paid --format all --out <new-directory>`.
- For a keyword, prepare the search plan and execute only the approved page.
  Read the actual candidates and preserve their original evidence. Select only
  candidates justified by the user's criteria; ask when ambiguous. Continue
  with `--resume <candidates-directory> --select-asins ...`, rather than searching
  again. Do not enlarge the original budget, change market or switch accounts.
- On partial results, read `result.json`, individual request errors, the dataset
  and reports. Deliver successful comparisons with their limits. If there is
  insufficient data, describe the gap rather than inventing a conclusion.

The plugin path selects `browser-account`. An independent legacy Skill selects
`env-api-key`; it never initializes browser credentials. Do not silently fall
back when either mode fails. If the selected browser connection is valid, do
not reconnect unnecessarily. Login consent is not approval for paid calls or
external mutations. Do not ask users to paste credentials into conversation.

Return clickable links to generated reports, a concise factual comparison and
the saved evidence directory. Keep missing currency, scale, sales and profit
unknown. The report is not proof of investment opportunity or current market
coverage. `--mock` and bundled samples are fictional and must be labeled.

Never replay a failed/uncertain paid invocation, change a keyword or automatically
expand candidates to manufacture success. Result retrieval is distinct from
resubmission. Respect server permission, preview and confirmation requirements.
Full tool discovery is `nexscope tools list`; catalog availability and a returned
task identifier do not establish successful end-to-end business acceptance.
