# Build Stage
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod ./
COPY main.go .
# COPY go.sum ./ 

RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o sidecar-proxy .

# Run Stage
FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/sidecar-proxy .

CMD ["./sidecar-proxy"]
