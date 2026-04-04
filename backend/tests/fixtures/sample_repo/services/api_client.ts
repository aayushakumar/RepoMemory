/**
 * API client for making HTTP requests.
 */

interface ApiConfig {
    baseUrl: string;
    timeout: number;
    headers: Record<string, string>;
}

interface ApiResponse<T> {
    data: T;
    status: number;
    ok: boolean;
}

export class ApiClient {
    private config: ApiConfig;

    constructor(config: Partial<ApiConfig> = {}) {
        this.config = {
            baseUrl: config.baseUrl || 'http://localhost:8080',
            timeout: config.timeout || 5000,
            headers: config.headers || {},
        };
    }

    async get<T>(path: string): Promise<ApiResponse<T>> {
        const response = await fetch(`${this.config.baseUrl}${path}`, {
            method: 'GET',
            headers: this.config.headers,
        });
        const data = await response.json();
        return { data, status: response.status, ok: response.ok };
    }

    async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
        const response = await fetch(`${this.config.baseUrl}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...this.config.headers,
            },
            body: JSON.stringify(body),
        });
        const data = await response.json();
        return { data, status: response.status, ok: response.ok };
    }

    setAuthToken(token: string): void {
        this.config.headers['Authorization'] = `Bearer ${token}`;
    }

    removeAuthToken(): void {
        delete this.config.headers['Authorization'];
    }
}

export function createApiClient(baseUrl: string): ApiClient {
    return new ApiClient({ baseUrl });
}
