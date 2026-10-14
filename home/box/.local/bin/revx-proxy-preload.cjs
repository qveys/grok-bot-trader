const { ProxyAgent, setGlobalDispatcher } = require("undici");
const proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.SAND_EGRESS_TUNNEL_PROXY_ADDR
  ? (process.env.HTTPS_PROXY || process.env.HTTP_PROXY || ("http://" + process.env.SAND_EGRESS_TUNNEL_PROXY_ADDR))
  : "http://127.0.0.1:8791";
setGlobalDispatcher(new ProxyAgent(proxy.startsWith("http") ? proxy : ("http://" + proxy)));
