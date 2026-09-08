(() => {
 "use strict";
 const PAIRS=[["AGP_COCKPIT_ACTION_BEGIN","AGP_COCKPIT_ACTION_END"],["AGP_COCKPIT_RESULT_BEGIN","AGP_COCKPIT_RESULT_END"],["AGP_COCKPIT_CONTROL_BEGIN","AGP_COCKPIT_CONTROL_END"]];
 function extract(text){
  const v=String(text||"").replace(/^\uFEFF/,"").replace(/[\u200B\u200C\u200D\u2060]/g,"").replace(/\r\n?/g,"\n").trim();
  const hits=PAIRS.filter(([b,e])=>v.includes(b)||v.includes(e)); if(hits.length!==1)throw Error("PHASE9_CANONICALIZER_FRAME_KIND_AMBIGUOUS");
  const [b,e]=hits[0],a=v.indexOf(b),z=v.indexOf(e,a+b.length); if(a<0||z<0||v.indexOf(b,a+b.length)>=0||v.indexOf(e,z+e.length)>=0)throw Error("PHASE9_CANONICALIZER_FRAME_AMBIGUOUS");
  return {b,e,p:v.slice(a+b.length,z).trim()};
 }
 function bend(s,start){const op=s[start];if(op!=="{"&&op!=="[")return-1;const st=[op];let ins=false,esc=false;for(let i=start+1;i<s.length;i++){const c=s[i];if(ins){if(esc)esc=false;else if(c==="\\")esc=true;else if(c==='"')ins=false;continue;}if(c==='"'){ins=true;continue;}if(c==="{"||c==="["){st.push(c);continue;}if(c==="}"||c==="]"){const w=c==="}"?"{":"[";if(st[st.length-1]!==w)return-1;st.pop();if(!st.length)return i;}}return-1;}
 function lost(p){const ms=[...p.matchAll(/"content"\s*:\s*"\s*([\{\[])/g)];if(ms.length!==1)return null;const m=ms[0],s=m.index+m[0].lastIndexOf(m[1]),e=bend(p,s);if(e<0)return null;let q=e+1;while(q<p.length&&/\s/.test(p[q]))q++;if(p[q]!=='"')return null;let inner;try{inner=JSON.parse(p.slice(s,e+1));}catch(_){return null;}const x=m.index+m[0].lastIndexOf('"'),fixed=p.slice(0,x)+JSON.stringify(JSON.stringify(inner))+p.slice(q+1);try{return JSON.parse(fixed);}catch(_){return null;}}
 function norm(o){if(!o||Array.isArray(o)||typeof o!=="object")return o;const k="work"+"_"+"order",w=o[k];if(!w||Array.isArray(w)||typeof w!=="object")return o;if(w.type==="terminal_payload"&&w.content!==null&&typeof w.content==="object"&&!Array.isArray(w.content))return {...o,[k]:{type:"terminal_payload",content:JSON.stringify(w.content)}};if(!Object.prototype.hasOwnProperty.call(w,"type")&&!Object.prototype.hasOwnProperty.call(w,"content")){const allowed=new Set(["kind","cwd","argv","timeout_seconds","label"]),ks=Object.keys(w);if(ks.length&&ks.every(x=>allowed.has(x))&&typeof w.cwd==="string"&&w.cwd.trim()&&Array.isArray(w.argv)&&w.argv.length&&w.argv.every(x=>typeof x==="string"&&x.length))return {...o,[k]:{type:"terminal_payload",content:JSON.stringify(w)}};}return o;}
 function canonicalizeProtocolFrame(text){const {b,e,p}=extract(text);let o;try{o=JSON.parse(p);}catch(_){o=lost(p);if(!o)throw Error("PHASE9_CANONICALIZER_INVALID_JSON");}if(!o||Array.isArray(o)||typeof o!=="object")throw Error("PHASE9_CANONICALIZER_PAYLOAD_NOT_OBJECT");o=norm(o);return `${b}\n${JSON.stringify(o)}\n${e}`;}
 globalThis.AGPCockpitProtocolCanonicalizerV1=Object.freeze({canonicalizeProtocolFrame});
})();
