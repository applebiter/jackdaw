SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;


CREATE TABLE `sounds` (
  `id` int UNSIGNED NOT NULL,
  `uuid` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `filename` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mimetype` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `extension` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `size` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `duration_timecode` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `duration_milliseconds` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `bits_per_sample` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `bitrate` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `channels` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `samplerate` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `beats_per_minute` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `genre` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `title` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `albumartist` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `album` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tracknumber` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `discnumber` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `artist` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `year` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `label` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `copyright` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `composer` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `producer` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `engineer` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `comment` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `created` datetime NOT NULL,
  `modified` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


ALTER TABLE `sounds`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uuid` (`uuid`),
  ADD UNIQUE KEY `location` (`location`,`filename`);


ALTER TABLE `sounds`
  MODIFY `id` int UNSIGNED NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
