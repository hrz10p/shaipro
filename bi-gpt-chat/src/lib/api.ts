const API_BASE_URL = 'https://bi-gpt.enbekqor.kz';

export interface ChatRequest {
  message: string;
  context?: string;
}

export interface ChartData {
  bin_start?: number;
  bin_end?: number;
  count?: number;
  pct?: number;
  [key: string]: any;
}

export interface ChartMeta {
  title: string;
  x_label: string;
  y_label: string;
  tooltip_fields: string[];
}

export interface Visualization {
  chart_type: 'histogram' | 'pie' | 'scatter' | 'line' | 'error' | 'none';
  meta: ChartMeta;
  data: ChartData[];
}

export interface ChatResponse {
  output: string;
  success: boolean;
  intermediate_steps: Array<{
    node: string;
    output: string | any;
  }>;
  route: string;
  sql: string;
  exec_result: any;
  visualization?: Visualization;
}

export interface ApiError {
  message: string;
  status?: number;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new ApiError(
          `HTTP error! status: ${response.status}, message: ${errorText}`,
          response.status
        );
      }

      const data: ChatResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  async clearMemory(): Promise<{success: boolean, message: string}> {
    try {
      const response = await fetch(`${this.baseUrl}/clear-memory`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
      });
      
      if (!response.ok) {
        throw new ApiError(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  }
}

export const apiService = new ApiService();

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}
