-- =============================================================================
-- Virtual Economist — Full Agent & App Schema
-- Matches the official schema diagram exactly.
-- Run AFTER setup.sql (which creates the users table).
--
-- Tables (exact names from diagram):
--   user_profiles              — display name + preferences JSONB (1:1 with users)
--   stored_chats               — one chat session per user
--   stored_messages            — individual message turns inside a chat
--   housing_data_embeddings    — static city snapshot: home value, income, weather
--   housing_time_series        — long-format Zillow time-series (EAV: one metric per row)
--   stock_data_embeddings      — company analyst / ownership snapshot
--   map_pins                   — lat/lng city markers for the map view
--   heat_map_data              — lat/lng points for heat-map overlays
--
-- Extensions required:
--   pgvector  (CREATE EXTENSION vector)
--   pg_trgm   (CREATE EXTENSION pg_trgm)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- =============================================================================
-- USER_PROFILES
--
-- One row per user.  `user_id` is the PK and the FK back to users.
-- `created_at` stored as BIGINT Unix epoch (matches diagram: INT / int8).
-- `preferences` JSONB holds arbitrary per-user settings.
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id      INT           PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(255),
    preferences  JSONB         NOT NULL DEFAULT '{}',
    created_at   BIGINT        NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
);


-- =============================================================================
-- STORED_CHATS
--
-- One row per conversation thread.  Diagram shows: id, user_id, created_at,
-- Users_id (FK → users.id).
--
-- Extensions beyond the diagram (needed for UI):
--   agent_type  TEXT  — 'housing' | 'market' (so frontend can group chats)
--   title       TEXT  — auto-generated or user-edited label
-- =============================================================================
CREATE TABLE IF NOT EXISTS stored_chats (
    id         SERIAL      PRIMARY KEY,
    user_id    INT         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- UI extensions (not in original diagram but required for chat sidebar)
    agent_type TEXT        CHECK (agent_type IN ('housing', 'market')),
    title      TEXT
);

CREATE INDEX IF NOT EXISTS idx_stored_chats_user_id
    ON stored_chats (user_id);

CREATE INDEX IF NOT EXISTS idx_stored_chats_user_agent
    ON stored_chats (user_id, agent_type, created_at DESC);


-- =============================================================================
-- STORED_MESSAGES
--
-- One row per message turn.  Diagram shows:
--   id, chat_id, sender (INT), message (TEXT), metadata (JSONB),
--   created_at (TIMESTAMP), embedding vector(1536)
--
-- sender encoding:
--   0 = user  (human message)
--   1 = agent (AI / system response)
--
-- metadata JSONB stores agent internals:
--   { "sql_used": "SELECT …", "rows_found": 12, "error": null }
--
-- embedding is nullable — populate it later for semantic history search.
-- =============================================================================
CREATE TABLE IF NOT EXISTS stored_messages (
    id         SERIAL        PRIMARY KEY,
    chat_id    INT           NOT NULL REFERENCES stored_chats(id) ON DELETE CASCADE,
    sender     INT           NOT NULL CHECK (sender IN (0, 1)),
    message    TEXT          NOT NULL,
    metadata   JSONB         NOT NULL DEFAULT '{}',
    created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding  vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_stored_messages_chat_id
    ON stored_messages (chat_id, created_at ASC);

-- Uncomment once you start populating embeddings:
-- CREATE INDEX IF NOT EXISTS idx_stored_messages_embedding
--     ON stored_messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);


-- =============================================================================
-- HOUSING_DATA_EMBEDDINGS  (static city snapshot)
--
-- One row per city.  metadata JSONB holds all structured attributes.
-- stored_messages_id is NULLABLE — links a data row to the message that
-- triggered its retrieval (populated by the agent pipeline if desired).
--
-- Expected metadata shape:
-- {
--   "city":                    "Philadelphia, Pennsylvania",
--   "median_home_value":       "380000",
--   "median_household_income": "60800",
--   "weather_by_month": {
--     "January-2024":  { "avg_temperature_f": "30", "min_temperature_f": "24",
--                        "max_temperature_f": "38", "precipitation_in": "3.1",
--                        "windspeed_mph": "11",     "snowfall_in": "5.2" },
--     "February-2024": { … },
--     … (all 12 months)
--   }
-- }
-- =============================================================================
CREATE TABLE IF NOT EXISTS housing_data_embeddings (
    id                  SERIAL        PRIMARY KEY,
    embedding           vector(1536),
    metadata            JSONB         NOT NULL DEFAULT '{}',
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stored_messages_id  INT           REFERENCES stored_messages(id) ON DELETE SET NULL
);

-- Cosine similarity vector search
CREATE INDEX IF NOT EXISTS idx_housing_emb_vector
    ON housing_data_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Fuzzy city-name filter used in WHERE similarity(…) > 0.3
CREATE INDEX IF NOT EXISTS idx_housing_emb_city_trgm
    ON housing_data_embeddings
    USING gin ((metadata->>'city') gin_trgm_ops);

-- Exact city lookup
CREATE INDEX IF NOT EXISTS idx_housing_emb_city_btree
    ON housing_data_embeddings ((metadata->>'city'));


-- =============================================================================
-- HOUSING_TIME_SERIES  (long-format / EAV Zillow data)
--
-- Source: Zillow Research Data exports.
-- Each row = one metric for one region on one date.
-- This is a "long" / EAV design: pivot with CASE WHEN metric = 'X' in queries.
--
-- Columns (exact from diagram):
--   RegionID    INTEGER
--   RegionName  TEXT        e.g. 'Austin' or 'Austin, TX'
--   RegionType  TEXT        'msa' | 'city' | 'zip' | 'county' | 'state'
--   StateName   TEXT        e.g. 'Texas'
--   metric      TEXT        'zhvi' | 'zori' | 'inventory' | 'new_listings' |
--                           'days_to_pending' | 'price_cuts' | ...
--   date        DATE        first day of the reported month
--   value       DOUBLE PRECISION
-- =============================================================================
CREATE TABLE IF NOT EXISTS housing_time_series (
    id          SERIAL            PRIMARY KEY,
    "RegionID"  INTEGER,
    "RegionName" TEXT             NOT NULL,
    "RegionType" TEXT,
    "StateName"  TEXT,
    metric      TEXT              NOT NULL,
    date        DATE              NOT NULL,
    value       DOUBLE PRECISION,

    UNIQUE ("RegionID", metric, date)   -- prevent duplicate imports
);

-- Fast city + metric + date lookups
CREATE INDEX IF NOT EXISTS idx_hts_region_metric_date
    ON housing_time_series ("RegionName", metric, date DESC);

-- Fuzzy region name search
CREATE INDEX IF NOT EXISTS idx_hts_regionname_trgm
    ON housing_time_series USING gin ("RegionName" gin_trgm_ops);

-- Filter by region type
CREATE INDEX IF NOT EXISTS idx_hts_regiontype
    ON housing_time_series ("RegionType");


-- =============================================================================
-- STOCK_DATA_EMBEDDINGS  (company analyst & ownership snapshot)
--
-- stored_messages_id is NULLABLE — links data to the message that retrieved it.
--
-- Expected metadata shape:
-- {
--   "name":                     "Apple Inc.",
--   "sector":                   "Technology",
--   "industry":                 "Consumer Electronics",
--   "recommendation":           "Strong Buy",
--   "insider_ownership":        "0.07",
--   "institutional_ownership":  "0.59"
-- }
-- =============================================================================
CREATE TABLE IF NOT EXISTS stock_data_embeddings (
    id                  SERIAL        PRIMARY KEY,
    embedding           vector(1536),
    metadata            JSONB         NOT NULL DEFAULT '{}',
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stored_messages_id  INT           REFERENCES stored_messages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_stock_emb_name_trgm
    ON stock_data_embeddings
    USING gin ((metadata->>'name') gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_stock_emb_sector
    ON stock_data_embeddings ((metadata->>'sector'));

CREATE INDEX IF NOT EXISTS idx_stock_emb_recommendation
    ON stock_data_embeddings ((metadata->>'recommendation'));


-- =============================================================================
-- MAP_PINS  (city markers for the real-estate map view)
--
-- `data` JSONB can hold display-layer extras: home value, icon colour, etc.
-- `created_at` stored as BIGINT Unix epoch (matches diagram: INT).
-- =============================================================================
CREATE TABLE IF NOT EXISTS map_pins (
    id         SERIAL            PRIMARY KEY,
    city       VARCHAR(255)      NOT NULL,
    latitude   DOUBLE PRECISION  NOT NULL,
    longitude  DOUBLE PRECISION  NOT NULL,
    data       JSONB             NOT NULL DEFAULT '{}',
    created_at BIGINT            NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
);

CREATE INDEX IF NOT EXISTS idx_map_pins_city
    ON map_pins (city);

-- Bounding-box queries: lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_map_pins_latlon
    ON map_pins (latitude, longitude);


-- =============================================================================
-- HEAT_MAP_DATA  (lat/lng points for choropleth / density overlays)
--
-- Matches diagram exactly: id, lat, lon, created_at (timestamp).
-- No value or data_type columns — those can be added via ALTER TABLE if needed.
-- =============================================================================
CREATE TABLE IF NOT EXISTS heat_map_data (
    id         SERIAL            PRIMARY KEY,
    lat        DOUBLE PRECISION  NOT NULL,
    lon        DOUBLE PRECISION  NOT NULL,
    created_at TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_heat_map_latlon
    ON heat_map_data (lat, lon);
