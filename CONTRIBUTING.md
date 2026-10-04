# Contributing to JAL-RAKSHA

Thank you for your interest in contributing to **JAL-RAKSHA**!

## Code of Conduct
We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful and constructive in all discussions.

## Getting Started
1. **Fork & Clone** the repository.
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

## Development Guidelines
- Always ensure all tests pass before submitting a pull request:
  ```bash
  pytest tests/ -q
  ```
- Maintain adherence to existing architectural separation (`app/routers/`, `app/services/`, `frontend/`).
- Preserve docstrings and model equations in `docs/` when changing hydrodynamic solvers.

## Pull Request Process
1. Create a descriptive feature branch (`git checkout -b feature/my-feature`).
2. Commit clear, concise commits.
3. Open a Pull Request against `main`.
