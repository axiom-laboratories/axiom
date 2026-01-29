package main

import (
	"log"
	"net/http"
	"os"
	"github.com/elazarl/goproxy"
)

func main() {
	proxy := goproxy.NewProxyHttpServer()
	proxy.Verbose = true

	// simple logic: Log every request
	proxy.OnRequest().DoFunc(
		func(r *http.Request, ctx *goproxy.ProxyCtx) (*http.Request, *http.Response) {
			log.Printf("[PROXY] Request: %s %s", r.Method, r.URL.String())
			return r, nil
		})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🛡️ Go Sidecar Proxy listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, proxy))
}
