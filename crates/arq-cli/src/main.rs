use anyhow::Result;
use clap::{Parser, Subcommand};

mod commands;
use commands::dev::{handle_dev, DevCommands};

#[derive(Parser)]
#[command(name = "arq")]
#[command(about = "The ArqonBus CLI", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Local Development Helpers
    Dev {
        #[command(subcommand)]
        cmd: DevCommands,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    // 1. Init Telemetry
    tracing_subscriber::fmt::init();

    // 2. Parse Args
    let cli = Cli::parse();

    // 3. Dispatch
    match &cli.command {
        Commands::Dev { cmd } => handle_dev(cmd)?,
    }

    Ok(())
}
