export class ConsentChainError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public response?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ConsentChainError";
  }
}

export class AuthenticationError extends ConsentChainError {
  constructor(message: string = "Authentication failed") {
    super(message, 401);
    this.name = "AuthenticationError";
  }
}

export class NotFoundError extends ConsentChainError {
  constructor(message: string = "Resource not found") {
    super(message, 404);
    this.name = "NotFoundError";
  }
}

export class ValidationError extends ConsentChainError {
  constructor(message: string, response?: Record<string, unknown>) {
    super(message, 422, response);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends ConsentChainError {
  constructor(message: string = "Rate limit exceeded", retryAfter?: number) {
    super(message, 429);
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }

  retryAfter?: number;
}
