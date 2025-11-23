run-debug:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 80 --proxy-headers --forwarded-allow-ips='*' --log-config=./logging/log_debug_conf.yml

run-dev:
	uv run uvicorn src.main:app --host 0.0.0.0 --port 80 --proxy-headers --forwarded-allow-ips='*' --log-config=./logging/log_debug_conf.yml

run-prod:
	uv run uvicorn src.main:app --host 0.0.0.0 --port 80 --proxy-headers --forwarded-allow-ips='*' --log-config=./logging/log_prod_conf.yml

migration-add:
	uv run alembic revision --autogenerate -m "$(name)"

database-upgrade:
	uv run alembic upgrade head

database-downgrade:
	uv run alembic downgrade -1

