CREATE TABLE IF NOT EXISTS `fuel_prices` (
   `window_start` TIMESTAMP NOT NULL,
   `window_end` TIMESTAMP NOT NULL,
   `post_code` CHAR(5) NOT NULL,
   `diesel` DECIMAL(4,3) NULL DEFAULT 0.0,
   `e5` DECIMAL(4,3) NULL DEFAULT 0.0,
   `e10` DECIMAL(4,3) NULL DEFAULT 0.0,
   PRIMARY KEY(`window_start`, `window_end`, `post_code`)
);
