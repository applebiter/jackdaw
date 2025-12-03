-- Music Library Database Schema for SQLite
-- Converted from MySQL xiphsound.sounds table

CREATE TABLE IF NOT EXISTS sounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    location TEXT NOT NULL,
    filename TEXT,
    mimetype TEXT NOT NULL,
    extension TEXT NOT NULL,
    filetype TEXT,
    size TEXT,
    duration_timecode TEXT,
    duration_milliseconds TEXT,
    bits_per_sample TEXT,
    bitrate TEXT,
    channels TEXT,
    samplerate TEXT,
    beats_per_minute TEXT,
    genre TEXT,
    title TEXT,
    albumartist TEXT,
    album TEXT,
    tracknumber TEXT,
    discnumber TEXT,
    artist TEXT,
    year TEXT,
    label TEXT,
    copyright TEXT,
    composer TEXT,
    producer TEXT,
    engineer TEXT,
    comment TEXT,
    created TEXT NOT NULL,
    modified TEXT NOT NULL,
    UNIQUE(location, filename)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_artist ON sounds(artist);
CREATE INDEX IF NOT EXISTS idx_album ON sounds(album);
CREATE INDEX IF NOT EXISTS idx_genre ON sounds(genre);
CREATE INDEX IF NOT EXISTS idx_title ON sounds(title);
CREATE INDEX IF NOT EXISTS idx_year ON sounds(year);
CREATE INDEX IF NOT EXISTS idx_albumartist ON sounds(albumartist);
