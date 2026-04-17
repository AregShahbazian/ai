# crypto_base_scanner Reference

> Source: `$CRYPTO_BASE_SCANNER_DIR` (branch: master)
> Git hash: `37c17d580aeba623a875832bd6b0558e5a86e868`
> Do NOT explore source — use this doc instead.

## Overview

Ruby on Rails 8.0 backend. Multiple Grape-based REST APIs (V3 main, V1/V2 external, CS, Internal, Partners) plus legacy Rails controllers at `/api/v2`. MySQL primary + PostgreSQL/TimescaleDB for time-series. Sidekiq for background jobs. AnyCable for WebSockets.

## Tech Stack

- **Framework**: Rails 8.0, Ruby 3.1.1+, Puma
- **Databases**: MySQL (primary), PostgreSQL/TimescaleDB (time-series)
- **Cache/Queue**: Redis (sessions, cache, Sidekiq)
- **APIs**: Grape (REST), Doorkeeper (OAuth2), Swagger docs
- **Auth**: JWT, OmniAuth (Google, Apple, Discord, Coinbase, Binance, KuCoin, OKX, Bybit, BitMart), WebAuthn, ROTP (2FA)
- **Jobs**: Sidekiq + Sidekiq-Scheduler
- **WebSockets**: AnyCable
- **Storage**: ActiveStorage + AWS S3
- **Payments**: Stripe, Mollie, CoinGate, Apple IAP
- **Monitoring**: New Relic, Sentry, Yabeda/Prometheus
- **Email**: ActionMailer + Customer.io
- **Frontend** (admin): React-Rails, Stimulus, Tailwind, HAML

## Authentication Patterns

| API | Auth method | Details |
|-----|------------|---------|
| V3 (main) | Token via `Authorization` header | Doorkeeper OAuth2, whitelisted public endpoints |
| V2 (legacy Rails) | `user_id` header or param | Account external_id, skip_before_action :authenticate! |
| External V2 | `api_key` + `secret` (HMAC) | Signal bot webhook auth |
| Internal | `INTERNAL_API_KEY` env var | Skipped in dev/test |
| CS | Same as V3 | Customer support admin |
| Partners V1 | `Altrady-Api-Key` + `Altrady-Signature` (HMAC-SHA256) + nonce | 5-second nonce window, Redis dedup |

V3 public whitelist (no auth): `/application_settings/shared/:id`, `/doc`, `/locales`, `/news`, `/preview`, `/latest_features`, `/subscription_plans`, `/subscription_terms`, `/sign_up`, `/sign_out`, `/login`, `/forgot_password`, `/signal_providers`, `/events`, `/exchanges`, `/currencies`, `/stats`, `/promotions`, `/trade_setups`, `/shared_items`, `/saved_images`

## API V2 — Legacy Rails Controllers

### TradingView Charts

`Api::V2::TradingviewChartsController` — chart storage and snapshot upload. Auth via `user_id` header (account external_id).

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET/POST | `/api/v2/tradingview_charts/*tv_version/:storage_type` | `chart`/`template` (opt) | List/load charts |
| POST | `/api/v2/tradingview_charts/*tv_version/:storage_type` | `name`, `content`, `symbol`, `resolution` | Save/update chart |
| DELETE | `/api/v2/tradingview_charts/*tv_version/:storage_type` | `chart`/`template` | Delete chart |
| POST | `/api/v2/tradingview_charts/snapshot` | `preparedImage` (file), `symbol` | Upload screenshot → hosted URL |

**Snapshot flow:** Creates `SavedImage`, attaches PNG via ActiveStorage, runs `SavedImageJob` (thumbnails: twitter 850x630, facebook 1200x630). Returns `https://app.altrady.com/x/:externalId`. Chart-engine-agnostic — accepts any PNG file.

## API V3 — Main App API (Grape)

### Notes

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/notes` | `coinray_symbol` (opt), `q` (search), pagination | List notes (fulltext search) |
| POST | `/notes` | `coinray_symbol` (req), `title`, `text`, `pinned`, `screenshot_url` | Create note |
| PATCH | `/notes/:id` | `coinray_symbol`, `title`, `text`, `pinned`, `screenshot_url` | Update note |
| DELETE | `/notes/:id` | — | Delete note |

**`screenshot_url`**: stored as-is (string column, no validation). Data URLs, hosted URLs, any string accepted.

### Account

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/account` | — | Get account status |
| GET | `/account/onboarding` | — | Onboarding progress |
| PATCH | `/account/onboarding` | `goal`, `experience`, `style`, `origin`, `features[]`, `status`, `goal_checklists`, `preset_checklists`, `survey_timings`, `api_key` (Hash), `force_reset` | Update onboarding |
| PATCH | `/account/account_preference` | `algorithm`, notification prefs | Update preferences |
| PATCH | `/account/profile` | `username`, `country`, `bio`, `website`, social links, `base64_avatar` | Update profile |
| POST | `/account/in_app_purchase` | `product_id`, `transaction_id`, `transaction_receipt` | Apple IAP |
| DELETE | `/account` | — | Deactivate account |

### Alerts

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/alerts` | `coinray_symbol` (opt), `status` ("pending"\|"delivered"), pagination | List alerts |
| POST | `/alerts` | `coinray_symbol`, `alert_type` ("price"\|"trend_line"\|"time"), `price`, `data`, `expires_at`, `recurring`, `direction`, `note`, `sound`, `webhook_url`, `webhook_enabled`, `webhook_payload` | Create alert |
| PATCH | `/alerts/:id` | Same as POST | Update alert |
| PATCH | `/alerts/:id/pause` | — | Pause alert |
| PATCH | `/alerts/:id/resume` | — | Resume alert |
| DELETE | `/alerts/:id` | — | Delete alert |

Max per market: 50. Max total: 1000.

### Orders

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/orders` | `exchange_api_key_id`, `coinray_symbol`, `status` ("open"\|"closed"), pagination (limit: 5000) | List orders |
| GET | `/orders/open_symbols` | `exchange_api_key_id` | Symbols with open orders |
| GET | `/orders/for_currency` | `currency`, pagination | Closed orders for currency |
| POST | `/orders/reserve` | `coinray_symbol`, `exchange_api_key_id`, `orders[]` | Reserve orders |
| DELETE | `/orders` | `exchange_api_key_id`, `order_external_ids[]` | Cancel orders |

### Smart Orders

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/smart_orders` | `coinray_symbol`, `exchange_api_key_id`, smart_order params | Create |
| DELETE | `/smart_orders/:id` | `exchange_api_key_id`, `coinray_symbol` | Cancel |

### Layered Orders

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/layered_orders` | `coinray_symbol`, `exchange_api_key_id`, layered_order params, `orders[]` | Create |
| DELETE | `/layered_orders` | `exchange_api_key_id`, `layered_order_id` | Cancel |

### Positions

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/positions` | `exchange_api_key_id`, `exchange_api_key_ids`, `status`, `position_types`, pagination | List |
| POST | `/positions` | `coinray_symbol`, `exchange_api_key_id`, `open_time`, `close_time`, `external_ids[]`, `signed_action`, `trade_plan_id` | Create |
| PATCH | `/positions/:id` | `open_time`, `close_time` | Update |
| PATCH | `/positions/:id/convert_to_smart_position` | `signed_action` | Convert to smart |
| DELETE | `/positions/:id` | — | Delete |
| POST | `/positions/:id/share` | `hide_amounts`, `save_image`, `published`, `title`, `description` | Share position |
| PATCH | `/positions/:id/share/:external_id` | Same | Update shared |

### Smart Positions

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/smart_positions` | `coinray_symbol`, `exchange_api_key_id`, `orders[]`, `smart_position`, `signed_action`, import params, `position_side`, `leverage`, `margin_type` | Create |
| GET | `/smart_positions/:id` | — | Get |
| PATCH | `/smart_positions/:id` | update params | Update |
| PATCH | `/smart_positions/:id/close` | `order_type` (MARKET\|LIMIT), `price` | Close |
| PATCH | `/smart_positions/:id/reduce` | `order_type`, `amount_type`, `close_fully`, amounts | Reduce |
| PATCH | `/smart_positions/:id/increase` | `order_type`, `amount_type`, amounts | Increase |
| DELETE | `/smart_positions/:id` | `exchange_api_key_id` | Delete |
| POST | `/smart_positions/:id/webhook_link` | `close_on_filled` | Create webhook |
| DELETE | `/smart_positions/:id/webhook_link` | — | Remove webhook |

### Trades

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/trades` | `coinray_symbol`, `exchange_api_key_id`, `status`, `limit` (0-1000, default 100), pagination | List trades |

### Trade Analytics

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/trade_analytics` | `exchange_api_key_ids`, `coinray_symbol`, `quote_currency`, `analytics_start`, `analytics_end` (unix ms) | P&L stats |

### Application Settings

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/application_settings` | `settings_type` (comma-separated) | Get by type |
| GET | `/application_settings/:id` | — | Get specific |
| GET | `/application_settings/shared/:share_id` | — | Get shared (public) |
| POST | `/application_settings` | `settings_type`, `name`, `current`, `share_enabled`, `version`, `serialized_settings` (Hash) | Create |
| PATCH | `/application_settings/:id` | Same as POST | Update |
| DELETE | `/application_settings/:id` | — | Delete |

Limits: 30 for watchlists, 10 for others, 50 for enterprise.

### TradingView Chart Storage (V3)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/tradingview/:storage_type` | `version` | List charts |
| GET | `/tradingview/:storage_type/:id` | — | Load chart |
| POST | `/tradingview/:storage_type` | `name`, `content`, `symbol`, `resolution`, `version` | Save chart |
| PATCH | `/tradingview/:storage_type/:id` | Same | Update |
| DELETE | `/tradingview/:storage_type/:id` | — | Delete |

### TradingView Drawings

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/tradingview/drawings/:chart_id` | `coinray_symbol` (req) | Get drawings |
| PATCH | `/tradingview/drawings/:chart_id` | `drawings` (Hash), `version` | Update (version control) |

### TradingView Drawing Templates

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/tradingview/drawing_templates` | `tool`, `version` | Get templates |
| POST | `/tradingview/drawing_templates` | `tool`, `version`, `name`, `template` | Save |
| PATCH | `/tradingview/drawing_templates/:id` | `name`, `template` | Update |
| DELETE | `/tradingview/drawing_templates/:id` | — | Delete |

### Balances

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/balances` | `statistics_start`, `statistics_end`, `exchange_api_key_ids`, `external_wallet_ids`, `stacked_data` | Full history |
| GET | `/balances/current` | — | Current overview |
| GET | `/balances/for_currency` | `currency` (req) | Balance for currency |
| GET | `/balances/for_api_key` | `exchange_api_key_id` (req) | Balance for API key |
| GET | `/balances/total` | `exchange_api_key_ids`, `external_wallet_ids` | Totals |
| GET | `/balances/stats` | `exchange_api_key_ids`, `external_wallet_ids` | Stats (day/month/year) |

### Exchange API Keys

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/exchange_api_keys` | `exchange_api_key_ids`, `statistics_start` | List with balances |
| POST | `/exchange_api_keys` | `exchange_code`, `settings`, `label`, `active`, `portfolio_folder_id`, `paper_trading`, `api_key_hash`, `proxy_id`, `async` | Create |
| PATCH | `/exchange_api_keys/:id` | Same (except exchange_code), plus `link_id` and `async` | Update |
| DELETE | `/exchange_api_keys/:id` | — | Mark inactive+DELETING, enqueue `DeleteExchangeApiKeyJob` |
| POST | `/exchange_api_keys/sync` | `exchange_api_key_id` | Sync exchange data |
| POST | `/exchange_api_keys/reset` | — | Reset vault |

### External Wallets

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/external_wallets` | `external_wallet_ids`, `other_currency` | List |
| POST | `/external_wallet` | `name`, `portfolio_folder_id` | Create |
| PATCH | `/external_wallet/:id` | `name`, `portfolio_folder_id` | Update |
| DELETE | `/external_wallet/:id` | — | Delete |

### Grid Bot Settings

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/grid_bot_settings` | pagination | List bots |
| GET | `/grid_bot_settings/:id` | — | Get bot (supports share_id) |
| POST | `/grid_bot_settings` | `exchange_api_key_id`, grid bot params | Create |
| PATCH | `/grid_bot_settings/:id` | grid bot params | Update |
| DELETE | `/grid_bot_settings/:id` | — | Delete |
| GET | `/grid_bot_settings/:id/trades` | — | Trades from last session |
| POST | `/grid_bot_settings/:id/fix` | — | Fix bot issues |
| PATCH | `/grid_bot_settings/start_stop` | `active`, `grid_bot_setting_ids[]`, `close_action` | Start/stop |
| PATCH | `/grid_bot_settings/update_status` | `state`, `grid_bot_setting_ids[]`, `close_action` | Pause/stop |
| PATCH | `/grid_bot_settings/:id/sharing` | `enable`, `is_public`, `description` | Share |
| GET | `/grid_bot_settings/:id/stats` | `type` (CHARTS\|TOTALS\|SESSIONS\|OPEN), `start_time`, `end_time` | Stats |
| GET | `/grid_bot_settings/backtests` | — | List backtests |
| GET | `/grid_bot_settings/backtests/:id` | — | Get backtest |
| POST | `/grid_bot_settings/backtest` | backtest params | Run backtest |
| DELETE | `/grid_bot_settings/backtests/:id` | — | Delete backtest |

### Signal Bot Settings

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/signal_bot_settings` | pagination | List bots |
| GET | `/signal_bot_settings/shared` | `partner_only`, `signal_provider_id`, `exchange_id`, `quote_currency`, `coinray_symbol`, pagination | Public bots |
| GET | `/signal_bot_settings/:id` | — | Get bot (supports share_id) |
| POST | `/signal_bot_settings` | `exchange_api_key_id`, `name`, `active`, `signed_action`, `position_settings`, `filters` | Create |
| PATCH | `/signal_bot_settings/:id` | Same | Update |
| DELETE | `/signal_bot_settings/:id` | — | Delete |
| PATCH | `/signal_bot_settings/:id/remove_cooldown` | — | Remove cooldown |
| PATCH | `/signal_bot_settings/start_stop` | `active`, `signal_bot_setting_ids[]` | Start/stop |
| PATCH | `/signal_bot_settings/:id/sharing` | `enable`, `is_public`, `description` | Share |
| GET | `/signal_bot_settings/:id/stats` | `type`, `start_time`, `end_time` | Stats |

### Bots (aggregated)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/bots/my_bots` | `query`, `bot_types`, `exchange_api_key_ids`, `status`, pagination | User's bots |
| GET | `/bots/public_bots` | `query`, `bot_types`, `partner_only`, `exchange_code`, `coinray_symbol`, pagination | Public bots |

### Saved Images & Shared Items

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/saved_images/:external_id` | — | Get saved image (public) |
| GET | `/shared_items` | `type` (POSITION\|BOT\|SIGNAL_BOT\|GRID_BOT\|TRADE_SETUP\|WATCHLIST\|LAYOUT\|SCREENSHOT), pagination | List (public) |
| GET | `/shared_items/:external_id` | — | Get shared item |
| PATCH | `/shared_items/:external_id/like` | — | Like |
| PATCH | `/shared_items/:external_id/unlike` | — | Unlike |
| GET | `/shared_items/:external_id/comments` | `sort`, pagination | Comments |
| POST | `/shared_items/:external_id/comments` | `comment` | Post comment |
| PATCH | `/shared_items/:external_id/comments/:id` | `comment` | Edit comment |
| DELETE | `/shared_items/:external_id/comments/:id` | — | Delete comment |

### Watchlist

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/watchlist` | — | Get |
| PATCH | `/watchlist` | `serialized_list` (String) | Update |
| PATCH | `/watchlist/restore` | — | Restore previous |

### Markets & Exchanges

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/markets/market_trading_info` | `coinray_symbol`, `exchange_api_key_id`, `sync` | Market info |
| POST | `/markets/sync` | `coinray_symbol`, `exchange_api_key_id` | Sync market |
| GET | `/exchanges` | — | List exchanges |
| GET | `/currencies/eur_to_usd` | — | EUR/USD rate |
| GET | `/currencies/usd_conversions` | — | USD conversions |

### Notification Rules

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/notification_rules` | — | List |
| POST | `/notification_rules` | `exchange_id`\|`exchange_code`, `volume`, `volume_type`, `drop`, `median_multiplier`, `mobile`, `desktop`, `quote_currencies[]` | Create |
| PATCH | `/notification_rules/:id` | Same | Update |
| DELETE | `/notification_rules/:id` | — | Delete |

### Dashboard

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/dashboard/positions` | `exchange_api_key_ids`, `status`, `time_period` (7\|30), `position_types` | Positions |
| GET | `/dashboard/bots_stats` | `exchange_api_key_ids` | Bot stats |
| GET | `/dashboard/balances` | `exchange_api_key_ids` | 30-day balance |
| GET | `/dashboard/tutorials` | — | Onboarding tutorials |
| GET | `/dashboard/youtube_videos` | — | Videos (cached 12h) |
| GET | `/dashboard/playlists` | — | Playlists (cached 12h) |

### Trade Setups

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/trade_setups` | — | Recent (public, limit 10) |
| GET | `/trade_setups/:external_id` | — | Get |
| POST | `/trade_setups` | `coinray_symbol`, `resolution`, `data`, `title`, `description`, `is_public`, `signal_provider_id` | Share |
| PATCH | `/trade_setups/:external_id/like` | — | Like |
| PATCH | `/trade_setups/:external_id/unlike` | — | Unlike |

### Portfolio Folders

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/portfolio_folders` | — | List |
| POST | `/portfolio_folders` | `name` | Create |
| PATCH | `/portfolio_folders/:id` | `name` | Update |
| DELETE | `/portfolio_folders/:id` | — | Delete |

### Devices

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/devices` | — | List devices |
| POST | `/devices` | `fcm_token`, `platform` | Register device |
| PATCH | `/devices/:id` | device params | Update |
| DELETE | `/devices/:id` | — | Unregister |

### Authentication

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/login` | `email_address`, `password`, `captcha` | Login |
| POST | `/sign_up` | `email_address`, `password`, `captcha`, `a` (affiliate) | Register |
| POST | `/sign_up/resend_confirmation` | `email_address` | Resend verification |
| GET | `/sign_up/check_confirmed` | `email_address` | Check confirmed |
| POST | `/sign_up/verification` | `token` | Verify email |
| GET | `/sign_out` | — | Logout |
| POST | `/forgot_password` | `email_address` | Password reset |

### Multi-Factor Auth

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/multi_factor/activate` | `otp_code` | Activate 2FA |
| POST | `/multi_factor/deactivate` | `otp_code` | Deactivate 2FA |
| POST | `/multi_factor/verify` | `otp_code` | Verify OTP |

### Futures

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/futures/positions` | `exchange_api_key_id`, `coinray_symbol` | Futures positions |

### Additional V3 Endpoints

- `/base_scanner` — base scanner data
- `/data_exports` — user data export
- `/exchange_imports` — trade import from exchanges
- `/global_notifications` — app notifications
- `/latest_features` — changelog
- `/news` — crypto news feed
- `/push_notifications` — push notification management
- `/preview` — account preview (no auth)
- `/quizzes` — quiz system
- `/surveys` — user surveys
- `/tutorials` — onboarding tutorials
- `/journal` — trading journal (strategies, trade plans)
- `/paper_trading` — paper trading management
- `/partners` — partner features
- `/promotions` — active promotions
- `/social_accounts` — linked social accounts
- `/stats` — platform statistics
- `/webauthn/*` — passkey auth

## External APIs

### API V1 (Public) — `/v1`

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| GET | `/bases` | `api_key`, `algorithm`, `exchanges` | List market bases (cached 1 min) |
| POST | `/events` | `api_key`, `event[name, external_id, source, data]` | Create event (sources: 3commas, gnosify) |

### API External V2 — `/v2` (Signal webhooks)

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/signal_bot_positions` | `api_key`, `api_secret`, action params | Webhook for signal bot actions |

Actions: `open`, `close`, `buy`, `sell`, `reverse`, `increase`, `reduce`, `start_bot`, `stop_bot`, `stop_and_close`, `start_and_open`. Supports TradingView dynamic variables (`{{exchange}}`, `{{ticker}}`).

### API Internal — `/api/internal`

| Method | Path | Params | Description |
|--------|------|--------|-------------|
| POST | `/voucher` | `external_id`, `discount`, `days` | Create voucher |
| POST | `/event` | `external_id`, `event_name`, `data` | Track event (public) |
| POST | `/trial_reset` | `external_id` | Reset trial |

### API CS (Customer Service) — `/api/cs`

16 endpoint modules: Accounts, Alerts, ApplicationSettings, Balances, BaseScannerSettings, Devices, ExchangeApiKeys, GridBots, Markets, PushNotifications, Payments, Positions, SignalBots, Subscriptions, Trading, TradingviewCharts, FastConnectAttempts.

### API Partners V1 — `/partner/v1`

7 endpoint modules: Accounts, Login, ExchangeApiKeys, VoucherCodes, SignalProviderCustomers, Signals, SignalBots, TradeSetups.

## Key Models

### Account
- `email_address`, `password_digest`, `external_id` (UUID), `confirmed_at`
- `otp_secret`, `multi_factor_activated` (2FA)
- Admin levels: NONE(0), NORMAL(1), SUPER(2)
- Password: 10-60 chars, uppercase+lowercase+special required, 5 attempts → 15 min block
- Has many: exchange_api_keys, orders, trades, positions, alerts, notes, saved_images, devices, grid/signal bot settings

### Subscription
- Plans: FREE, TRADING_ONLY, SCANNER, ADVANCED, PRO
- Terms: 1MONTH, 3MONTHS, 12MONTHS
- Features: SIGNALS, TRADING, ADVANCED_TRADING, PORTFOLIO, TRADING_ANALYTICS, MOBILE, API, BASE_SCANNER, SMART_ORDERS, TREND_LINE_ALERTS
- `can_use?(feature)`, `get_limit(type, default)`

### Exchange
- `code` (BINA, BTRX, etc), `name`, `tv_exchange`, `is_futures`, `active`
- `supported_order_types`, `supported_features`
- `supports_feature?(feature)`

### Market
- `symbol`, `coinray_symbol`, `base_currency`, `quote_currency`, `last_price`
- Status: ACTIVE, DELISTED, INACTIVE
- `current_price` (from Redis or fallback), `leveraged?`
- Associations: bases, alerts, triggers, market_stats, candle_hours

### ExchangeApiKey
- `label`, `exchange_id`, `active`, `paper_trading`, `trading_enabled`
- Status: ACTIVE, INACTIVE, INVALID_API_KEY, RATE_LIMITED, SUBSCRIPTION_EXPIRED, RESET, NEEDS_WRAPPING, DELETING
- `settings` (JSON, encrypted credentials), `ws_token` (JSON)
- Paper trading: initialized with 10k balance
- DELETE flow: controller sets `active=false, status=DELETING`, enqueues `DeleteExchangeApiKeyJob` which batch-deletes orders, trades, positions, trade_days, futures_positions, signal/grid bot records, balances, then the key itself

### Order
- Sides: BUY, SELL
- Types: LIMIT, MARKET, STOP_LOSS, OCO
- States: OPEN, PENDING, COOLING_DOWN, CLOSED, CANCELED, FAILED, STALE
- `external_id` (exchange ID), `linked_order` (polymorphic for smart orders)

### SpotPosition (STI base)
- Status: PENDING, OPEN, CLOSED, CANCELED, ERROR
- Side: long, short
- `positionable` (polymorphic → SmartPosition, GridBotSession, FuturesPosition)
- `calculation_cache` (JSON, cached P&L calculations)

### SmartPosition (extends SpotPosition)
- `smart_settings` (JSON: entry conditions, exit targets, stop loss, leverage)
- `webhook_key`, `webhook_settings`
- Can convert to/from SpotPosition

**Entry condition** (`SmartPosition::EntryCondition`): `price`, `operator` (OR/AND), `direction`, `price_enabled`, `time_enabled`, `start_at`, `candle_close`, `candle_resolution`. When `candle_close_enabled?` (candle_close && candle_resolution > 0), a price hit sets `candle_close_triggered` and defers activation until the next candle-close boundary (`next_candle_close_time`); if price no longer meets the condition before close, the trigger resets. Exposed on `ApiV3::Entities::SmartSettings::EntryCondition`.

### Alert
- Types: price, time, trend_line
- Status: pending, paused, delivered, triggered, expired
- `webhook_url`, `webhook_enabled`, `recurring`
- Triggers: PriceTrigger, TimeTrigger, TrendLineTrigger

### PriceTrigger
- `price`, `direction` (up/down), `triggerable` (polymorphic)
- States: PENDING, TRIGGERED, TIMEOUT, DISABLED, CANCELED
- Push to Redis for fast checking

### Note
- `coinray_symbol`, `title`, `text`, `pinned`, `screenshot_url` (plain string, no validation)
- Fulltext search via MATCH AGAINST

### SavedImage
- `external_id`, `status`, `title`, `description`, `view_count`
- ActiveStorage: `original_image`, `image` (variants: twitter 850x630, facebook 1200x630)
- Auto-generates title/description from market data

### SharedItem
- Types: POSITION, BOT, SIGNAL_BOT, GRID_BOT, TRADE_SETUP, TRADE_PLAN, WATCHLIST, LAYOUT, SCREENSHOT
- `origin` (polymorphic), `published`, `view_count`, `comments_count`
- ActiveStorage: `chart_portrait`, `chart_landscape`, `image`, `card_image`
- Votable (acts_as_votable)

### ApplicationSetting
- `settings_type`, `name`, `version`, `serialized_settings` (JSON)
- `current` (boolean), `share_id`
- Types: market-watchlists, trading_terminal_layout, etc.

### TradingviewChart
- `content` (JSON, TV chart state), `disabled`, `account_id`
- Has many: tradingview_drawings

### GridBotSetting / GridBotSession
- Setting: `active`, `upper_price`, `lower_price`, `number_of_orders`, `allow_trailing_up/down`, `position_settings` (JSON)
- Session: `status` (starting/running/processing/paused/stopping/stopped/error), `version` (v2/v3), `settings` (JSON clone), `statistics` (JSON)

### SignalBotSetting / SignalBotPosition
- Setting: `active`, `signal_provider_type` (SIGNAL_PROVIDER/WEBHOOK), `filters` (JSON), `position_settings` (JSON), `secret_digest`
- Position: `status` (new/creating/running/closed/canceled/error/deleted), `signal_data` (JSON)

### FuturesPosition
- `side` (LONG/SHORT/BOTH), `quantity`, `leverage`, `margin_type`, `liquidation_price`
- `position_mode` (HEDGE/ONE_WAY)

## Services

### Trading::CoinrayService
Primary exchange trading interface. Key methods:
- `fetch_balance()`, `fetch_open_orders(market)`, `fetch_closed_orders(market)`, `fetch_trades(market)`, `fetch_positions()`
- `create_order(market, options)`, `update_order(market, options)`, `cancel_order(market, order, options)`
- `set_position_mode(market, mode)`, `set_margin_type(market, type)`, `set_leverage(market, leverage)`
- `create_signed_action()`, `fetch_ws_token()`, `test(credential)`
- Class methods: `signed_request(method, url, body)` — low-level signed HTTP; `verify_vault(credential, encrypted_password)` — verify JWE-encrypted vault password against Coinray `/api/v2/credentials/verify`
- Wrapped in `safe_execute` with error handling (InvalidKey, InsufficientBalance, etc.)

### Markets::CoinrayService
Market data from Coinray API:
- `load_markets()`, `load_prices()`, `load_hour_candles(market)`, `load_minute_candles(market)`
- `load_currencies(date)`, `load_summaries(resolution)`, `announce_new_markets()`

### BalanceCalculationServiceV2
- `total(api_keys, wallets, days_ago=2)` — totals
- `full(api_keys, wallets, start, end, num_days=50, stacked_data=false)` — history

### BalancesProcessService
- `process(exchange_api_key, balances, broadcast=true)` — process balance updates, broadcast via UserChannel

### TradeProcessService
- `process_market(market, exchange_api_key, trades)` — process new trades, create records, trigger recalculations

### PaperTradingService
Simulated trading with real market data (largest service, 10k+ lines).

### BacktestTradingService
Extends MockTradingService for historical backtesting. `check_orders(low, high)`.

### PushNotificationService
- `send_market_notification(devices, msg, market, type, options)` — FCM push
- `send_link_notification(devices, msg, url, type, options)`
- Web devices receive via ActionCable instead of FCM

### SharePositionService
Server-side chart screenshot generation via HtmlToPngService for position sharing.

### Other Services
HtmlToPngService, HtmlToPdfService, QrCodeGeneratorService, MollieService, StripeService, CoinGateService, CustomerIOService, DiscordService, NewsService, AffiliateSettlementService, JsonWebTokenService, CodeAuthenticatorService, RefundService, GA4Service, FacebookAdsService, SocialShareService, SearchService

## Background Jobs (Sidekiq)

### Exchange sync (every 1 min)
- `ScheduleExchangeSyncJob` → `ExchangeSyncJob` (per API key) → fetches balances, positions, orders, trades. Broadcasts `EXCHANGE_SYNC` events (STARTED/FINISHED/ERROR) via `UserChannel`. Skips API keys in `DELETING` state.
- `DeleteExchangeApiKeyJob` — batch-deletes all related records (Order, Trade, SpotPosition, TradeDay, FuturesPosition, SignalBotPosition/Setting, GridBotSetting/Session, ExchangeBalance) in 5k-row batches, then deletes the key.

### Market data (every 30s)
- `UpdateMarketsJob` → `Markets::CoinrayService.load_prices()`

### Candles & bases (every 15 min)
- `ScheduleLoadCandlesJob` → `LoadCandlesJob` → `CheckBasesJob` (every 1 min)

### Alert triggers (every 1-5 sec)
- `ScheduleCheckTriggerableJob` (every 1 min) → `CheckPriceTriggersJob`
- `ScheduleAlertExpirationsJob` (every 5 sec) → expire stale alerts
- `TriggerAlertJob` → push/email/webhook

### Bot execution
- `GridBotSessionJob` — grid bot operations (start, restart, pause, stop, fix)
- `SignalBotJob` — process incoming signals, create positions
- `ScheduleFaultyGridBotSessionsJob` (every 5 min)
- `ScheduleBotExpirationsJob` (every 10 sec)

### Other scheduled jobs
- `SubscriptionSchedulerJob` — daily at 10:00
- `CleanupJob` — daily at 7:00
- `OrderCleanupJob` — daily at midnight
- `CalculatePriceSignalsJob` — daily at 8:00
- `FetchRssFeedsJob` — every 15 min
- `CleanupOldNewsJob` — daily at 6:00
- `ExchangeBalanceBackfillJob` — daily at 00:05
- `MolliePaymentEnhancerJob` — hourly at :15
- `UpdateVatRatesJob` — daily at 9:00

## WebSocket (AnyCable)

### UserChannel
Primary real-time channel. Broadcasts via `UserChannel.broadcast_to(account, message)`.

Events:
- `BALANCE_UPDATED` — balance changed
- `BALANCE_UPDATES` — detailed balance updates
- `TRADE_UPDATES` — new trades executed
- `PUSH_NOTIFICATION` — push notification (web)
- `RATE_LIMITED` — API rate limit hit
- `BOTS_UPDATED` — bot status changed
- `MARKET_UPDATED` — market data updated
- `EXCHANGE_SYNC` — exchange sync lifecycle (data: `{exchangeApiKeyId, status: STARTED|FINISHED|ERROR, message?}`)

Auth: JWT token from query params → Session#token → current_account.

Also publishes to external WebSocket via `$websocket` (channel: `account-stream.#{account.external_id}`).

## Public Routes

| Path | Description |
|------|-------------|
| `/share/:external_id` | Shared items page |
| `/x/:code` | Screenshot share page |
| `/s/:short_url` | Short URL redirect |
| `/ts/:external_id` | Trade setup share |

## Payment Webhooks

| Path | Provider |
|------|----------|
| `/mollie/webhook` | Mollie |
| `/coingate/webhook` | CoinGate |
| `/webhook/heyflow` | HeyFlow |
| `/webhook/coindelist` | CoindeList |
| `/webhook/calendly` | Calendly |

## Entity Serialization

All V3 entities extend `BaseEntity` (Grape::Entity). Field names auto-camelCased. Formatting helpers: `int_to_iso8601`, `decimal`, `float`, `default_decimal`. Pagination headers: `X-Total`, `X-Page`, `X-Page-Per`.
