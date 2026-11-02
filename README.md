# BookNest 📚

**BookNest** is a modern, lightweight, stateless online book catalog web application. Designed for cloud-native deployment, it serves an interactive book directory with live search, category filtering, book additions, and deletions.

The application is container-ready and stateless, storing catalog records in memory seeded from `data/books.json` upon initialization, making it ideal for containerization with Docker and orchestration on Kubernetes (EKS).

---

## Features

- **Live Search & Filter:** Filter books instantaneously by title or author keywords alongside category dropdown filtering.
- **Add New Books:** Add books with client-side and server-side validation (title, author, category, price) and immediate catalog update.
- **Delete Books:** Remove books dynamically with interactive confirmation dialogues.
- **Cloud-Native & Container-Ready:** Built-in `/health` endpoint designed for Kubernetes liveness and readiness probes.
- **Stateless & In-Memory:** Fast startup, seeded from JSON, with no external database dependencies.
- **Clean Responsive UI:** Pure HTML5, CSS3, and vanilla JavaScript without external JS frameworks or frontend build tooling.

---

## Project Structure

```text
booknest-app/
├── app/
│   ├── __init__.py        # Flask application factory
│   ├── routes.py          # API and web route handlers
│   ├── catalog.py         # Thread-safe in-memory book catalog
│   ├── templates/
│   │   └── index.html     # Application HTML template (contains brand heading)
│   └── static/
│       ├── style.css      # Modern responsive styling
│       └── app.js         # Frontend interactions and API integrations
├── data/
│   └── books.json         # Seed catalog (10 sample books across 5 categories)
├── tests/
│   ├── __init__.py
│   └── test_app.py        # Pytest test suite
├── wsgi.py                # WSGI entrypoint for Gunicorn
├── requirements.txt       # Pinned production and test dependencies
├── Dockerfile             # Multi-stage/slim container specification (python:3.12-slim)
├── .dockerignore
├── .gitignore
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web application home page |
| `GET` | `/health` | Health check endpoint for container probes (returns `{"status": "ok"}`) |
| `GET` | `/api/books` | Returns books, optionally filtered by `?q=<term>` and `?category=<category>` |
| `GET` | `/api/categories`| Returns all unique book categories |
| `POST` | `/api/books` | Adds a new book (JSON body with `title`, `author`, `category`, `price`) |
| `DELETE` | `/api/books/<id>`| Deletes a book by ID (returns 404 if not found) |

---

## Local Development

### 1. Prerequisites
- Python 3.12+ (or compatible Python 3 environment)
- `pip`

### 2. Setup Virtual Environment & Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 3. Run Locally

**Using Flask Development Server:**
```bash
flask --app wsgi:app run --port 5000
```

**Using Gunicorn (Production WSGI server):**
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Open your browser at [http://localhost:5000](http://localhost:5000).

---

## Running Tests

Run the test suite using `pytest`:

```bash
source .venv/bin/activate
pytest -v
```

The test suite covers:
- `/health` probe endpoint
- Index page and version display
- Full catalog listing
- Search by keyword (`q`) and category (`category`)
- Adding books with valid and invalid payloads
- Deleting existing and non-existent books

---

## Docker Build & Run

The included `Dockerfile` uses `python:3.12-slim`, configures a non-root user (`appuser`), includes a built-in `HEALTHCHECK`, and executes `gunicorn` on port 5000.

### 1. Build the Docker Image

```bash
docker build -t booknest:latest .
```

### 2. Run the Container

```bash
docker run -d --name booknest -p 5000:5000 booknest:latest
```

### 3. Verify Health and Access

- Application: [http://localhost:5000](http://localhost:5000)
- Health Check: [http://localhost:5000/health](http://localhost:5000/health)

To view container status and inspect the healthcheck:
```bash
docker inspect --format='{{json .State.Health.Status}}' booknest
```

To stop and remove the container:
```bash
docker stop booknest && docker rm booknest
```

---

## CI/CD and Deployment

BookNest uses a GitOps delivery pipeline. A push to `main` builds, tests, and publishes an image, then updates a separate GitOps repository. Argo CD watches that repository and reconciles the cluster toward the desired state.

### Architecture Flow

```text
Developer
   │  git push to main
   ▼
GitHub (booknest-app)
   │  triggers workflow
   ▼
GitHub Actions
   ├─ test ...................... pytest
   ├─ build-and-push ............ image tagged with short git SHA ──▶ Amazon ECR
   └─ update-gitops ............. updates image tag ─────────────────▶ booknest-gitops repo
                                                                              │
                                                                              ▼
                                                                          Argo CD
                                                                              │  sync (prune + selfHeal)
                                                                              ▼
                                                                          Amazon EKS
                                                                          namespace: booknest
```

- **AWS authentication:** GitHub OIDC via `AWS_ROLE_ARN`; no long-lived AWS access keys are stored.
- **Image tags:** short git SHA (`${GITHUB_SHA::7}`), so every deployment is traceable and immutable.
- **GitOps source of truth:** `prathameshpp-007/booknest-gitops`, path `k8s`.

### Setup Checklist

1. **Create the ECR repository** (for example `booknest`) in the target AWS region.
2. **Configure GitHub OIDC in AWS:** add GitHub as an IAM OIDC provider, then create an IAM role whose trust policy is restricted to this repository and the `main` branch. Grant it permission to push to the ECR repository. Store the role ARN as the `AWS_ROLE_ARN` GitHub secret.
3. **Set GitHub Actions variables** (repository settings → Variables):
   - `AWS_REGION` — for example `us-east-1`
   - `ECR_REPOSITORY` — for example `booknest`
4. **Create a GitOps token:** generate a fine-grained token or PAT with write access to `prathameshpp-007/booknest-gitops` and store it as the `GITOPS_TOKEN` GitHub secret.
5. **Create the GitOps repository:** copy the contents of `gitops/k8s/` into the `k8s/` directory of `booknest-gitops`. Replace the `ACCOUNT_ID`, `REGION`, and `INITIAL` placeholders in `deployment.yaml` with real values, or let the first successful pipeline run set the image tag.
6. **Install Argo CD on the EKS cluster** and apply `gitops/argocd/application.yaml` (update `repoURL` if you fork the GitOps repository). The Application targets the `booknest` namespace with automated sync, pruning, self-healing, and namespace creation enabled.
7. **Push to `main`** to trigger the pipeline. Follow the run in the GitHub Actions tab; Argo CD will roll out the new image once the GitOps repository is updated.

> The `gitops/` folder is a staging area for the separate GitOps repository. The existing `k8s/` folder and `kind-config.yaml` remain untouched for local kind development.

