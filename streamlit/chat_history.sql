DROP TABLE IF EXISTS claim CASCADE;
DROP TABLE IF EXISTS input CASCADE;
DROP TABLE IF EXISTS metrics CASCADE;
DROP TABLE IF EXISTS source_type CASCADE;

CREATE TABLE IF NOT EXISTS source_type (
    source_type_id INT GENERATED ALWAYS AS IDENTITY,
    source_type_name VARCHAR(50) UNIQUE NOT NULL,
    PRIMARY KEY (source_type_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    metrics_id INT GENERATED ALWAYS AS IDENTITY,
    supported FLOAT NOT NULL,
    contradicted FLOAT NOT NULL,
    misleading FLOAT NOT NULL,
    unsure FLOAT NOT NULL,
    PRIMARY KEY (metrics_id)
);

CREATE TABLE IF NOT EXISTS input (
    input_id INT GENERATED ALWAYS AS IDENTITY,
    input_text TEXT NOT NULL,
    input_summary VARCHAR(255) NOT NULL,
    source_type_id INT NOT NULL,
    metrics_id INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (input_id),
    FOREIGN KEY (source_type_id) REFERENCES source_type(source_type_id) ON DELETE SET NULL,
    FOREIGN KEY (metrics_id) REFERENCES metrics(metrics_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS claim (
    claim_id INT GENERATED ALWAYS AS IDENTITY,
    input_id INT NOT NULL,
    claim_text TEXT NOT NULL,
    rating TEXT NOT NULL,
    evidence TEXT NOT NULL,
    sources TEXT[] NOT NULL,
    PRIMARY KEY (claim_id),
    FOREIGN KEY (input_id) REFERENCES input(input_id) ON DELETE CASCADE
);

-- PERFORMANCE INDEX to speed up streamlit chat history retrieval
CREATE INDEX IF NOT EXISTS idx_input_created_at ON input(created_at DESC);