import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Settings, Database, Shield, CheckCircle } from "lucide-react";

interface IntermediateStep {
  node: string;
  output: any;
}

interface IntermediateStepsProps {
  steps: IntermediateStep[];
}

export const IntermediateSteps = ({ steps }: IntermediateStepsProps) => {
  const getStepIcon = (action: string) => {
    switch (action) {
      case 'sql_metainfo':
        return <Database className="w-4 h-4" />;
      case 'sql_policies':
        return <Shield className="w-4 h-4" />;
      case 'sql_exec':
        return <CheckCircle className="w-4 h-4" />;
      default:
        return <Settings className="w-4 h-4" />;
    }
  };
  
  const getStepLabel = (action: string) => {
    switch (action) {
      case 'sql_metainfo':
        return 'Получение метаданных';
      case 'sql_policies':
        return 'Проверка политик';
      case 'sql_exec':
        return 'Выполнение запроса';
      default:
        return action;
    }
  };
  
  const getStepColor = (action: string) => {
    switch (action) {
      case 'sql_metainfo':
        return 'bg-accent/10 text-accent border-accent/20';
      case 'sql_policies':
        return 'bg-warning/10 text-warning border-warning/20';
      case 'sql_exec':
        return 'bg-success/10 text-success border-success/20';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };
  
  return (
    <Card className="bg-muted/30">
      <CardContent className="p-4">
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-3">
              {/* Step Number */}
              <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                {index + 1}
              </div>
              
              {/* Step Content */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  {getStepIcon(step.node)}
                  <span className="text-sm font-medium">
                    {getStepLabel(step.node)}
                  </span>
                  <Badge 
                    variant="outline" 
                    className={`text-xs px-2 py-0.5 ${getStepColor(step.node)}`}
                  >
                    {step.node}
                  </Badge>
                </div>
                
                {/* Step Result */}
                <div className="ml-6">
                  {typeof step.output === 'object' ? (
                    <ScrollArea className="max-h-32">
                      <pre className="text-xs bg-muted p-3 rounded border text-muted-foreground overflow-x-auto">
                        {JSON.stringify(step.output, null, 2)}
                      </pre>
                    </ScrollArea>
                  ) : (
                    <div className="text-xs text-muted-foreground bg-muted p-2 rounded border">
                      {String(step.output)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};