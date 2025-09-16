import { ChatInterface } from "@/components/ChatInterface";
import { Brain, Database } from "lucide-react";
import { useChat } from "@/hooks/useChat";

const Index = () => {
  const { isConnected } = useChat();

  return (
    <div className="min-h-screen bg-gradient-secondary">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                BI-GPT
              </h1>
              <p className="text-sm text-muted-foreground">
                Аналитика данных с помощью ИИ
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Chat Interface */}
      <main className="h-[calc(100vh-80px)]">
        <ChatInterface />
      </main>
    </div>
  );
};

export default Index;