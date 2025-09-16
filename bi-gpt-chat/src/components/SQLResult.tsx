import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Database, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { ChatResponse } from "@/lib/api";

interface SQLResultProps {
  response: ChatResponse;
}

export const SQLResult = ({ response }: SQLResultProps) => {
  // Parse the reply to extract SQL and results
  const parseReply = (reply: string) => {
    const sqlMatch = reply.match(/SQL:\s*\n([\s\S]*?)\n\n/);
    const resultsMatch = reply.match(/Results:\s*(\[[\s\S]*?\])/);
    const rowsMatch = reply.match(/Rows returned:\s*(\d+)/);
    
    const sql = sqlMatch ? sqlMatch[1].trim() : '';
    let results: any[] = [];
    
    if (resultsMatch) {
      try {
        results = JSON.parse(resultsMatch[1]);
      } catch (e) {
        console.error('Failed to parse results:', e);
      }
    }
    
    const rowCount = rowsMatch ? parseInt(rowsMatch[1]) : 0;
    
    return { sql, results, rowCount };
  };
  
  const { sql, results, rowCount } = parseReply(response.reply);
  
  // Get column names from first result
  const columns = results.length > 0 ? Object.keys(results[0]) : [];
  
  return (
    <div className="space-y-4">
      {/* Success/Error Indicator */}
      {response.success ? (
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Запрос выполнен успешно</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-red-600">
          <XCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Ошибка выполнения запроса</span>
        </div>
      )}
      
      {/* SQL Query */}
      {sql && (
        <Card className={response.success ? "" : "border-red-200 bg-red-50"}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Database className="w-4 h-4" />
              SQL Query
              {!response.success && (
                <Badge variant="destructive" className="text-xs">
                  Ошибка
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative">
              <ScrollArea className="max-h-40">
                <pre className={`text-xs p-4 rounded-md overflow-x-auto ${
                  response.success 
                    ? "bg-code-bg text-white" 
                    : "bg-red-100 text-red-800 border border-red-200"
                }`}>
                  <code className={response.success ? "text-sql-highlight" : ""}>{sql}</code>
                </pre>
              </ScrollArea>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Results */}
      {results.length > 0 && response.success && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Результаты</CardTitle>
              <Badge variant="outline" className="text-xs">
                {rowCount} строк
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-60 w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    {columns.map((column) => (
                      <TableHead key={column} className="text-xs font-medium">
                        {column}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row, index) => (
                    <TableRow key={index}>
                      {columns.map((column) => (
                        <TableCell key={column} className="text-xs">
                          {typeof row[column] === 'string' && row[column].includes('T00:00:00')
                            ? new Date(row[column]).toLocaleDateString()
                            : String(row[column])
                          }
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {!response.success && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-4 h-4" />
              Сообщение об ошибке
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-red-700 bg-red-100 p-3 rounded-md">
              {response.reply}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};