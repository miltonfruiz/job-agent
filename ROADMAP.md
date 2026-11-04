# Roadmap

Job Application Agent started as a hackathon project and I'm continuing it as a personal project. This roadmap lists the work I plan to do next, in priority order.

## 1. Grounding for the cover letter
Today the grounding check verifies that the tailored CV doesn't invent skills. The cover letter is not verified yet.
- [ ] Extract claims (skills, years of experience, tools) from the generated letter
- [ ] Check each claim against the source CV and flag unsupported ones
- [ ] Add a regeneration loop: if the letter fails grounding, retry with the flagged claims as constraints
- [ ] Surface grounding results for the letter at the human approval checkpoint
- [ ] Unit tests for the new node, including letters that try to inflate experience

## 2. Tests and robustness of the graph
- [ ] Unit tests for each node of the LangGraph pipeline, with the LLM mocked
- [ ] Error handling and retries for LLM API failures and rate limits
- [ ] Input validation: empty vacancy, very long vacancy, malformed CV, non-Spanish postings
- [ ] Structured logging of each node's input and output for easier debugging
- [ ] Refactor shared prompt and state-handling code out of individual nodes

## 3. Reproducibility and CI
- [ ] Dockerfile and docker-compose for the API and Postgres
- [ ] GitHub Actions workflow running lint and tests on every push
- [ ] Pin dependency versions and document the setup in `docs/REPRODUCTION.md`

## 4. Input formats (stretch)
- [ ] Accept CVs as PDF and DOCX, not only plain text
- [ ] Export the tailored CV and letter as PDF

## 5. Application history API (stretch)
- [ ] Endpoint to list and fetch past applications stored in Postgres
- [ ] Use stored history to avoid repeating the same ATS keyword mistakes across applications

## Out of scope
- Scraping job boards or auto-submitting applications
- Storing real personal data: the repo only uses synthetic sample CVs and postings
