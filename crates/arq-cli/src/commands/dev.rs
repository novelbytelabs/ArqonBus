use clap::Subcommand;
use std::process::Command;
use anyhow::Result;
use tracing::info;

#[derive(Subcommand)]
pub enum DevCommands {
    /// Start the local development stack
    Up,
    /// Stop the local development stack
    Down,
}

pub fn handle_dev(cmd: &DevCommands) -> Result<()> {
    match cmd {
        DevCommands::Up => {
            info!("Starting ArqonBus Dev Stack...");
            let status = Command::new("docker")
                .args(&["compose", "-f", "deploy/docker-compose.yml", "up", "-d"])
                .status()?;
            
            if status.success() {
                info!("Stack is UP! Dashboard: http://localhost:3000");
            } else {
                anyhow::bail!("Failed to start stack");
            }
        }
        DevCommands::Down => {
            info!("Stopping ArqonBus Dev Stack...");
            let status = Command::new("docker")
                .args(&["compose", "-f", "deploy/docker-compose.yml", "down"])
                .status()?;
             
            if status.success() {
                info!("Stack is DOWN");
            }
        }
    }
    Ok(())
}
