from __future__ import annotations

import json

import typer

from tis.planner.recommender import PlannerService
from tis.planner.workload import load_request

app = typer.Typer(help="Recommend hardware for LLM fine-tuning workloads.")
market_app = typer.Typer(help="Inspect normalized market offers and provider health.")
app.add_typer(market_app, name="market")
service = PlannerService()


@app.command()
def validate(
    config: str = typer.Argument(..., help="Path to a YAML or JSON planning request."),
) -> None:
    request = load_request(config)
    typer.echo("Config is valid.")
    typer.echo(
        f"Model={request.workload.model.name} | optimize_for={request.preference.optimize_for} "
        f"| platforms={','.join(request.constraints.platforms)}"
    )


@app.command()
def recommend(
    config: str = typer.Argument(..., help="Path to a YAML or JSON planning request."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table or json."),
) -> None:
    request = load_request(config)
    run = service.run(request)

    if output == "json":
        typer.echo(json.dumps(run.response.model_dump(mode="json"), indent=2))
        return

    typer.echo(run.response.summary)
    _print_provider_statuses(run.response.provider_statuses)
    if not run.response.recommendations:
        raise typer.Exit(code=1)

    for index, item in enumerate(run.response.recommendations, start=1):
        typer.echo(
            f"[{index}] {item.label:<9} "
            f"{item.config.gpu_count}x {item.config.gpu} on {item.config.platform} "
            f"| source={item.source} "
            f"| cost=${item.metrics.cost_usd:.2f} "
            f"| time={item.metrics.time_hours:.2f}h "
            f"| availability={item.availability.score:.2f}/{item.availability.risk}"
        )


@app.command()
def explain(
    config: str = typer.Argument(..., help="Path to a YAML or JSON planning request."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table or json."),
) -> None:
    request = load_request(config)
    run = service.run(request)
    if output == "json":
        typer.echo(json.dumps(run.model_dump(mode="json"), indent=2))
        return

    typer.echo(run.response.summary)
    typer.echo(
        "Estimate: "
        f"vram={run.estimate.required_vram_gb:.2f}GB "
        f"cpu={run.estimate.required_cpu_cores} "
        f"ram={run.estimate.required_ram_gb:.2f}GB "
        f"flops={run.estimate.total_flops:.3e}"
    )
    _print_provider_statuses(run.response.provider_statuses)
    typer.echo(f"Normalized offers considered: {len(run.market.offers)}")
    for recommendation in run.response.recommendations:
        typer.echo(f"\n- {recommendation.label.upper()}: {recommendation.config.gpu_count}x {recommendation.config.gpu}")
        typer.echo(f"  Platform: {recommendation.config.platform} ({recommendation.source})")
        typer.echo(
            f"  Metrics: cost=${recommendation.metrics.cost_usd:.2f} "
            f"| time={recommendation.metrics.time_hours:.2f}h "
            f"| util={recommendation.metrics.gpu_utilization:.0%}"
        )
        typer.echo(f"  Availability: {recommendation.availability.score:.2f} ({recommendation.availability.risk})")
        if recommendation.notes:
            for note in recommendation.notes:
                typer.echo(f"  Note: {note}")
        typer.echo(f"  Logic: {recommendation.explanation}")


@market_app.command("probe")
def market_probe(
    config: str = typer.Argument(..., help="Path to a YAML or JSON planning request."),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table or json."),
) -> None:
    request = load_request(config)
    run = service.run(request)
    if output == "json":
        typer.echo(json.dumps([status.model_dump(mode="json") for status in run.response.provider_statuses], indent=2))
        return
    _print_provider_statuses(run.response.provider_statuses)


@market_app.command("dump-offers")
def dump_offers(
    config: str = typer.Argument(..., help="Path to a YAML or JSON planning request."),
    output: str = typer.Option("json", "--output", "-o", help="Output format: json or table."),
) -> None:
    request = load_request(config)
    run = service.run(request)
    if output == "json":
        typer.echo(json.dumps([offer.model_dump(mode="json") for offer in run.market.offers], indent=2))
        return

    _print_provider_statuses(run.response.provider_statuses)
    for offer in run.market.offers:
        typer.echo(
            f"{offer.platform:<8} {offer.gpu_count}x {offer.gpu:<12} "
            f"region={offer.region:<12} source={offer.source:<6} "
            f"price=${offer.price_per_hour:.4f}/h vram={offer.vram_gb:.0f}GB"
        )


def _print_provider_statuses(statuses) -> None:
    typer.echo("Providers:")
    for status in statuses:
        state = "ok" if status.ok else "issue"
        message = status.message or ""
        typer.echo(
            f"- {status.provider:<8} state={state:<5} source={status.source:<6} "
            f"offers={status.offers_count:<3} {message}"
        )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
