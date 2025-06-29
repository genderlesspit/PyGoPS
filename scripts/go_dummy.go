package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

// Server configuration
type Config struct {
	Port        int    `json:"port"`
	Host        string `json:"host"`
	DatabaseURL string `json:"database_url"`
	RedisURL    string `json:"redis_url"`
	LogLevel    string `json:"log_level"`
	JWTSecret   string `json:"jwt_secret"`
	ConfigFile  string `json:"config_file"`
	ProjectDir  string `json:"project_dir"`
	Debug       bool   `json:"debug"`
	EnableCORS  bool   `json:"enable_cors"`
	EnableMetrics bool `json:"enable_metrics"`
	MaxConnections int `json:"max_connections"`
}

func main() {
	// Define flags for all possible kwargs
	var config Config

	flag.IntVar(&config.Port, "port", 3000, "Server port")
	flag.StringVar(&config.Host, "host", "localhost", "Server host")
	flag.StringVar(&config.DatabaseURL, "database_url", "", "Database connection URL")
	flag.StringVar(&config.RedisURL, "redis_url", "", "Redis connection URL")
	flag.StringVar(&config.LogLevel, "log_level", "info", "Log level")
	flag.StringVar(&config.JWTSecret, "jwt_secret", "", "JWT secret key")
	flag.StringVar(&config.ConfigFile, "config_file", "", "Configuration file path")
	flag.StringVar(&config.ProjectDir, "project_dir", ".", "Project directory")
	flag.BoolVar(&config.Debug, "debug", false, "Enable debug mode")
	flag.BoolVar(&config.EnableCORS, "enable_cors", false, "Enable CORS")
	flag.BoolVar(&config.EnableMetrics, "enable_metrics", false, "Enable metrics endpoint")
	flag.IntVar(&config.MaxConnections, "max_connections", 100, "Maximum connections")

	flag.Parse()

	// Print startup information
	fmt.Printf("🚀 Go Dummy Server Starting\n")
	fmt.Printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
	fmt.Printf("Host:           %s\n", config.Host)
	fmt.Printf("Port:           %d\n", config.Port)
	fmt.Printf("Project Dir:    %s\n", config.ProjectDir)
	fmt.Printf("Debug Mode:     %t\n", config.Debug)
	fmt.Printf("Log Level:      %s\n", config.LogLevel)

	if config.DatabaseURL != "" {
		fmt.Printf("Database:       %s\n", config.DatabaseURL)
	}
	if config.RedisURL != "" {
		fmt.Printf("Redis:          %s\n", config.RedisURL)
	}
	if config.JWTSecret != "" {
		fmt.Printf("JWT Secret:     %s\n", maskSecret(config.JWTSecret))
	}
	if config.ConfigFile != "" {
		fmt.Printf("Config File:    %s\n", config.ConfigFile)
	}

	fmt.Printf("CORS Enabled:   %t\n", config.EnableCORS)
	fmt.Printf("Metrics:        %t\n", config.EnableMetrics)
	fmt.Printf("Max Conns:      %d\n", config.MaxConnections)
	fmt.Printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

	// Setup HTTP handlers
	http.HandleFunc("/", handleRoot)
	http.HandleFunc("/health", handleHealth)
	http.HandleFunc("/config", func(w http.ResponseWriter, r *http.Request) {
		handleConfig(w, r, config)
	})
	http.HandleFunc("/echo", handleEcho)

	if config.EnableMetrics {
		http.HandleFunc("/metrics", handleMetrics)
		fmt.Printf("📊 Metrics endpoint: http://%s:%d/metrics\n", config.Host, config.Port)
	}

	// Start server
	addr := fmt.Sprintf("%s:%d", config.Host, config.Port)
	fmt.Printf("🌐 Server URL: http://%s:%d\n", config.Host, config.Port)
	fmt.Printf("💚 Health check: http://%s:%d/health\n", config.Host, config.Port)
	fmt.Printf("⚙️  Config endpoint: http://%s:%d/config\n", config.Host, config.Port)
	fmt.Printf("\n🎯 Server ready! Press Ctrl+C to stop.\n\n")

	log.Fatal(http.ListenAndServe(addr, nil))
}

func handleRoot(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"message":   "🚀 PyGoPS Go Dummy Server",
		"timestamp": time.Now().UTC(),
		"method":    r.Method,
		"path":      r.URL.Path,
		"headers":   r.Header,
		"remote":    r.RemoteAddr,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC(),
		"uptime":    time.Since(time.Now()).String(), // This would be tracked in real server
		"version":   "1.0.0",
		"go_version": fmt.Sprintf("%s", os.Getenv("GOVERSION")),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}

func handleConfig(w http.ResponseWriter, r *http.Request, config Config) {
	// Mask sensitive data
	configCopy := config
	if configCopy.JWTSecret != "" {
		configCopy.JWTSecret = maskSecret(configCopy.JWTSecret)
	}
	if configCopy.DatabaseURL != "" && len(configCopy.DatabaseURL) > 20 {
		configCopy.DatabaseURL = configCopy.DatabaseURL[:20] + "..."
	}

	response := map[string]interface{}{
		"config":    configCopy,
		"timestamp": time.Now().UTC(),
		"pid":       os.Getpid(),
		"args":      os.Args,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleEcho(w http.ResponseWriter, r *http.Request) {
	body := make(map[string]interface{})
	if r.Body != nil {
		json.NewDecoder(r.Body).Decode(&body)
	}

	response := map[string]interface{}{
		"echo": map[string]interface{}{
			"method":      r.Method,
			"url":         r.URL.String(),
			"headers":     r.Header,
			"query":       r.URL.Query(),
			"body":        body,
			"remote_addr": r.RemoteAddr,
			"timestamp":   time.Now().UTC(),
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleMetrics(w http.ResponseWriter, r *http.Request) {
	metrics := map[string]interface{}{
		"metrics": map[string]interface{}{
			"requests_total":      42,  // Mock data
			"requests_per_second": 1.5,
			"memory_usage_mb":     45.2,
			"cpu_usage_percent":   12.3,
			"goroutines":          8,
			"uptime_seconds":      300,
		},
		"timestamp": time.Now().UTC(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metrics)
}

func maskSecret(secret string) string {
	if len(secret) <= 8 {
		return "****"
	}
	return secret[:4] + "****" + secret[len(secret)-4:]
}