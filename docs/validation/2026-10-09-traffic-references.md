# Traffic reference validation, 2026-10-09

#46 extends the existing reference tool without adding a registry command. Its default weekday behavior remains covered. Opt-in annual windows disclose leap-day clamping and weekday mismatch; rolling references use observed same-weekday daily medians with declared support, formula and omitted dates. Combined references share one attempt budget and report conflicting signs or unavailable references explicitly.

Local validation: the full Python suite passes 1,861 tests. New fixtures cover leap years, the DST calendar boundary, absent prior-year dates, missing history, explicit zeros, a historical spike, incompatible references, provider failure without retry, source identities and invalid inputs rejected before access. Evidence descriptors distinguish provider date observations, derived medians/deltas, local policies and unverified caller context. The default can still use early calendar dates without requiring an unused historical window.

The versioned incident/business ledger is bounded caller input. No registry is fetched or authoritative source verified. Retrieval age and date overlap are local rules; relevance, collection health and causality stay unknown. Separate GSC/GA4 triage retains its existing source/unit/window gates. These are controlled transports and arithmetic fixtures, not a live Google check or expert diagnostic evaluation. #6 remains the gate for claims about diagnostic quality.

Each nested breakdown retains its own fingerprint and provenance. Its fingerprint does not cover the added historical query or caller ledger. The wrapper counts all attempted queries but has no aggregate output-byte parameter or durable evidence storage.
