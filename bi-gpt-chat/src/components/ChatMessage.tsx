import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronUp, Database, User, Bot, CheckCircle, XCircle } from "lucide-react";
import { SQLResult } from "./SQLResult";
import { IntermediateSteps } from "./IntermediateSteps";

import { ChatMessage as ChatMessageType } from "@/hooks/useChat";

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const [showSteps, setShowSteps] = useState(false);
  
  const isUser = message.sender === 'user';
  
  return (
    <div className={`flex gap-4 mb-6 animate-fade-in ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-chat-user' : 'bg-primary'
      }`}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>
      
      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        <Card className={`p-4 ${
          isUser 
            ? 'bg-chat-user text-white ml-auto' 
            : 'bg-card border'
        }`}>
          <div className="space-y-3">
            {/* Basic Message */}
            <div className="text-sm leading-relaxed">
              {message.content}
            </div>
            
            {/* Timestamp */}
            <div className={`text-xs opacity-70 ${isUser ? 'text-right' : 'text-left'}`}>
              {message.timestamp.toLocaleTimeString()}
            </div>
            
            {/* API Response for Assistant */}
            {!isUser && message.apiResponse && (
              <div className="space-y-4 mt-4">
                {/* Tool Used Badge and Success Status */}
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  <Badge variant="secondary" className="text-xs">
                    {message.apiResponse.tool_used}
                  </Badge>
                  {message.apiResponse.success ? (
                    <Badge variant="default" className="text-xs bg-green-100 text-green-700 border-green-200">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Успешно
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="text-xs">
                      <XCircle className="w-3 h-3 mr-1" />
                      Ошибка
                    </Badge>
                  )}
                </div>
                
                {/* SQL Result */}
                <SQLResult response={message.apiResponse} />
                
                {/* Intermediate Steps */}
                {message.apiResponse.tool_result.intermediate_steps && 
                 message.apiResponse.tool_result.intermediate_steps.length > 0 && (
                  <Collapsible open={showSteps} onOpenChange={setShowSteps}>
                    <CollapsibleTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="w-full justify-between text-muted-foreground hover:text-foreground"
                      >
                        <span className="text-xs">Промежуточные шаги ({message.apiResponse.tool_result.intermediate_steps.length})</span>
                        {showSteps ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2">
                      <IntermediateSteps steps={message.apiResponse.tool_result.intermediate_steps} />
                    </CollapsibleContent>
                  </Collapsible>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};