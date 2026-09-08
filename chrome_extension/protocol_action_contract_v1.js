(()=>{
"use strict";
const VERSION=1;
const ACTION_MODES=Object.freeze(["DIRECT_EXECUTION","FILE_TRANSFER"]);
const FORBIDDEN_PROTOCOL_MODE_ALIASES=Object.freeze(["COPY_PASTE"]);
const BROWSER_LLM_INSTRUCTION=[
  "AGP Cockpit Protocol v1 action contract:",
  "- action.mode MUST be exactly DIRECT_EXECUTION or FILE_TRANSFER.",
  "- COPY_PASTE is legacy/UI communication terminology and MUST NEVER be emitted as Protocol-v1 action.mode.",
  "- DIRECT_EXECUTION means the complete local work order is transported/executed directly.",
  "- FILE_TRANSFER means the complete local work order invokes the canonical Kit FILE_TRANSFER path; Cockpit still only transports it.",
  "- Do not invent, alias, translate, infer, or repair mode values.",
  "- Presentation syntax may be canonicalized, but semantic fields remain strict."
].join("\\n");
globalThis.AGPCockpitProtocolActionContractV1=Object.freeze({VERSION,ACTION_MODES,FORBIDDEN_PROTOCOL_MODE_ALIASES,BROWSER_LLM_INSTRUCTION});
})();
