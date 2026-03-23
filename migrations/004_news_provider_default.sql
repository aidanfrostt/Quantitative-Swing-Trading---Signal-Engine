-- Align DB default with current ingestion (Perigon). Safe if already 'perigon'.
ALTER TABLE news_articles ALTER COLUMN provider SET DEFAULT 'perigon';
