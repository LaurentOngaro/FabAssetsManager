# Contributing

Thank you for your interest in improving our application !

## Development Workflow

1. **Fork** the repository.
2. **Clone** your fork locally.
3. **Create a branch** for your changes.
4. **Install dependencies**: `pip install -r requirements.txt`.
   - Ensure `curl_cffi` is installed for Cloudflare bypass testing.
5. **Tests**: Run `pytest` to ensure no regressions in the cache or parser modules.
6. **Run the app**: `python app.py`.
7. **Commit** your changes and push to your fork.
8. **Submit a Pull Request**.
9. **Documentation**: Update `.github/SPEC.md` for architectural changes and `API_GUIDE.md` for new endpoints.

## Coding Standards

- Follow PEP 8 for Python code.
- Ensure all new features are documented in `API_GUIDE.md` if applicable.
- Update the `CHANGELOG.md` with your changes.

## Important Note

Always test your changes with a valid `config/cookies.txt` and `config/user_agent.txt` to ensure the Fab.com integration still works correctly.
