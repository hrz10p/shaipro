import { useState, useCallback, useEffect } from 'react';
import { apiService, ChatRequest, ChatResponse, ApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  apiResponse?: ChatResponse;
  isLoading?: boolean;
}

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const { toast } = useToast();

  const checkConnection = useCallback(async () => {
    const connected = await apiService.healthCheck();
    setIsConnected(connected);
    return connected;
  }, []);

  // Check connection on mount
  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  const sendMessage = useCallback(async (content: string, context?: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: content.trim(),
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      content: '',
      sender: 'assistant',
      timestamp: new Date(),
      isLoading: true
    };

    setMessages(prev => [...prev, loadingMessage]);

    try {
      const request: ChatRequest = {
        message: content.trim(),
        ...(context && { context })
      };

      const response = await apiService.sendMessage(request);

      // Remove loading message and add response
      setMessages(prev => 
        prev.filter(msg => msg.id !== loadingMessage.id).concat({
          id: (Date.now() + 2).toString(),
          content: response.reply,
          sender: 'assistant',
          timestamp: new Date(),
          apiResponse: response
        })
      );

      setIsConnected(true);

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Remove loading message
      setMessages(prev => prev.filter(msg => msg.id !== loadingMessage.id));

      const errorMessage = error instanceof ApiError 
        ? error.message 
        : 'Произошла неизвестная ошибка';

      const statusCode = error instanceof ApiError ? error.status : undefined;

      // Show appropriate error message
      if (statusCode === 0) {
        toast({
          title: "Ошибка подключения",
          description: "Не удалось подключиться к серверу. Проверьте, что бэкенд запущен на localhost:8001",
          variant: "destructive"
        });
        setIsConnected(false);
      } else if (statusCode && statusCode >= 500) {
        toast({
          title: "Ошибка сервера",
          description: "Сервер временно недоступен. Попробуйте позже.",
          variant: "destructive"
        });
      } else {
        toast({
          title: "Ошибка",
          description: errorMessage,
          variant: "destructive"
        });
      }

      // Add error message to chat
      const errorChatMessage: ChatMessage = {
        id: (Date.now() + 2).toString(),
        content: "Извините, произошла ошибка при обработке вашего запроса. Проверьте подключение к серверу.",
        sender: 'assistant',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorChatMessage]);

    } finally {
      setIsLoading(false);
    }
  }, [isLoading, toast]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    isConnected,
    sendMessage,
    clearMessages,
    checkConnection
  };
};
