"""Force Binance spot market data through data-api.binance.vision (api.binance.com is geo-blocked 451)."""
import ccxt
_orig = ccxt.binance
def _binance(config=None):
    cfg = dict(config or {})
    opts = dict(cfg.get('options') or {})
    opts.setdefault('defaultType', 'spot')
    opts.setdefault('fetchMarkets', ['spot'])
    cfg['options'] = opts
    cfg.setdefault('timeout', 120000)
    ex = _orig(cfg)
    try:
        ex.urls['api']['public'] = 'https://data-api.binance.vision/api/v3'
    except Exception:
        pass
    return ex
ccxt.binance = _binance
