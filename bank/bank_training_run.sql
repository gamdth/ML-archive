-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: bank
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `training_run`
--

DROP TABLE IF EXISTS `training_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `training_run` (
  `run_id` int NOT NULL AUTO_INCREMENT,
  `bank_id` int DEFAULT NULL,
  `dataset_id` int DEFAULT NULL,
  `model_id` int DEFAULT NULL,
  `run_date` datetime DEFAULT NULL,
  `iteration_number` int DEFAULT NULL,
  `performance_metric` decimal(5,4) DEFAULT NULL,
  `full_report_path` varchar(512) DEFAULT NULL,
  `is_best_model` tinyint(1) DEFAULT '0',
  `status` enum('Completed','Failed','Retained','Deleted','Pending') DEFAULT NULL,
  PRIMARY KEY (`run_id`),
  KEY `bank_id` (`bank_id`),
  KEY `dataset_id` (`dataset_id`),
  KEY `model_id` (`model_id`),
  CONSTRAINT `training_run_ibfk_1` FOREIGN KEY (`bank_id`) REFERENCES `bank` (`bank_id`),
  CONSTRAINT `training_run_ibfk_2` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`dataset_id`),
  CONSTRAINT `training_run_ibfk_3` FOREIGN KEY (`model_id`) REFERENCES `ml_model` (`model_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `training_run`
--

LOCK TABLES `training_run` WRITE;
/*!40000 ALTER TABLE `training_run` DISABLE KEYS */;
INSERT INTO `training_run` VALUES (1,3,2,2,'2025-10-28 15:01:58',1,NULL,NULL,0,'Pending');
/*!40000 ALTER TABLE `training_run` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-03 10:16:47
