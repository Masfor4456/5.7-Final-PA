# Final Project – Option 2: Column Family Database

## Author
Mason Ford

## Overview

This project is a Python application that demonstrates CRUD operations using a NoSQL Column Family database with Apache Cassandra.

The application uses the provided `FinalPA-Dataset.json` dataset and stores review information in two Cassandra tables:

- `ReviewData` – Stores review information such as review ID, product ID, reviewer ID, star rating, review title, review body, language, and product category.
- `ProductData` – Stores product information associated with the reviews.

## Technologies Used

- Python 3
- Apache Cassandra
- Cassandra Python Driver
- JSON
- Ubuntu Linux

## Requirements

The following software is required:

- Python 3
- Apache Cassandra
- Python Cassandra Driver

Install the Cassandra Python driver with:

```bash
pip3 install cassandra-driver
