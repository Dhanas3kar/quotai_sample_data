# QuotAI - Interview Guide

This guide contains concise, technically accurate explanations of the QuotAI data migration prototype, tailored for a Data Migration Engineer role.

## 60-Second Project Explanation
"QuotAI is a modular Python data-processing prototype I built to simulate an ETL migration pipeline. I took an existing cost-estimation codebase and built a migration layer in front of it to ingest imperfect legacy CSV data. The pipeline performs structural and referential validation, maps legacy schemas to a normalized target format, applies transformations, and isolates bad records into a quarantine file. It then generates a reconciliation report to prove data wasn't lost, and ensures the whole operation is idempotent. It's a localized, testable simulation of the core concepts you'd find in a larger data migration."

## Architecture Explanation
"The architecture intentionally decouples the migration pipeline from the business logic. 
It starts with a CLI Orchestrator. 
Data flows from legacy CSVs into a Validation layer that returns structured result objects. 
Valid data moves into a Transformer that applies schema mappings and normalization rules. 
Invalid data goes to a Quarantine module. 
Finally, target CSVs are generated alongside a Reconciliation report. 
The downstream QuotAI cost-estimation engine can then consume the clean target data entirely independently of how the migration happened."

## Common Q&A

**1. Why did you choose CSV?**
"CSV is universally understood and great for localized prototypes. It forces you to deal with string conversion, missing values, and data type validation manually, which perfectly simulates the messy reality of legacy system extracts without needing heavy database infrastructure for a local portfolio piece."

**2. Why did you separate validation from transformation?**
"Separation of concerns. A record should only be transformed if it's fundamentally valid. If transformation and validation are mixed, you often end up with complex try-catch blocks failing mid-transformation, making it hard to properly quarantine the exact raw record with a clear error reason."

**3. How do you handle invalid records?**
"Instead of silently dropping them or crashing the pipeline, the validator returns a structured result. If `is_valid` is False, the orchestrator routes the raw row, the record ID, and the specific error message to a `rejected_records.csv` file. This allows engineers to investigate and correct the data independently."

**4. How does reconciliation work?**
"The orchestrator counts exactly how many records came from the source, how many passed validation, how many were rejected, and how many unique target records were generated. The reconciliation report verifies that `source = valid + rejected`, proving no records disappeared into the void."

**5. How does idempotency work?**
"Running the pipeline twice with the same inputs shouldn't duplicate records. I enforce this by tracking unique identifiers (like `material_id` + `effective_date`) during the run. In this prototype, it prevents duplicates from being written to the output file. In production, this translates directly to database `UPSERT` statements."

**6. Why use Decimal for financial calculations?**
"Floating point arithmetic introduces precision errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). For the core cost-estimations and material rates, using Python's `Decimal` ensures exact arithmetic representation."

**7. How would you scale this system?**
"Currently, it loads entire CSVs into memory. To scale, I would shift from list comprehensions to stream processing (reading and yielding row by row using Python generators) or use a framework like Pandas/PySpark for chunking. I'd also move the target output into an actual relational database like PostgreSQL."

**8. What happens if a source CSV is malformed?**
"If the file is structurally malformed (e.g. missing columns), the `schema_validator` flags it immediately and the record goes to quarantine as `MISSING_REQUIRED`. If the CSV is so malformed that Python's `csv` module can't parse it, it throws an exception—handling that gracefully would be the next improvement."

**9. How do you prevent data loss?**
"Through the quarantine process and the reconciliation report. Every source row is accounted for mathematically. If the reconciliation math (`source == valid + rejected`) fails, the pipeline logs an error, alerting us that data might have been lost in memory."

**10. What are the current limitations?**
"It runs in-memory, so it wouldn't handle 10 million rows well. Also, referential integrity is only checked against the current batch of data being migrated, not against a live target database containing historical records."
