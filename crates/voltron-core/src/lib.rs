pub mod config {
    use serde::Deserialize;

    #[derive(Debug, Deserialize, Clone)]
    pub struct ServerConfig {
        pub host: String,
        pub port: u16,
    }

    #[derive(Debug, Deserialize, Clone)]
    pub struct NatsConfig {
        pub url: String,
    }

    #[derive(Debug, Deserialize, Clone)]
    pub struct AppConfig {
        pub server: ServerConfig,
        pub nats: NatsConfig,
    }
}
