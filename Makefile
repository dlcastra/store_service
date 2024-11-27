# commands for up
up-all:
	docker compose -f compose.yaml -f compose_payment_service.yaml up --build
up-main:
	docker compose -f compose.yaml up --build
up-cps:
	docker compose -f compose_payment_service.yaml up --build

# commands for single
down-all:
	docker compose -f compose.yaml -f compose_payment_service.yaml down
down-main:
	docker compose -f compose.yaml down
down-cps:
	docker compose -f compose.yaml down
