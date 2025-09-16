import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Wifi, WifiOff, RotateCcw } from "lucide-react";

interface ConnectionStatusProps {
  isConnected: boolean;
  onRetry: () => void;
  onClearChat: () => void;
  hasMessages: boolean;
}

export const ConnectionStatus = ({ 
  isConnected, 
  onRetry, 
  onClearChat, 
  hasMessages 
}: ConnectionStatusProps) => {
  return (
    <div className="px-4 py-2 border-b bg-background/95">
      <div className="max-w-4xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-sm text-green-600">Подключено к серверу</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-600">Сервер недоступен</span>
            </>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <Badge variant={isConnected ? "default" : "destructive"}>
            {isConnected ? "Online" : "Offline"}
          </Badge>
          
          {hasMessages && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearChat}
              className="text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Очистить чат
            </Button>
          )}
          
          {!isConnected && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Повторить
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
