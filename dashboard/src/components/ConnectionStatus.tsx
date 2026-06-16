import { memo, useMemo, useCallback } from 'react';
import { Wifi, WifiOff, AlertTriangle, RotateCcw, Users, Clock } from 'lucide-react';

interface ConnectionStatusProps {
  status: 'connected' | 'connecting' | 'disconnected' | 'error';
  latency?: number;
  clientCount?: number;
  uptime?: number;
  lastUpdate?: string;
  connectionQuality?: 'excellent' | 'good' | 'poor' | 'unknown';
  onReconnect?: () => void;
  className?: string;
}

export const ConnectionStatus = memo<ConnectionStatusProps>(({
  status,
  latency = 0,
  clientCount = 0,
  uptime = 0,
  lastUpdate = '',
  connectionQuality = 'unknown',
  onReconnect,
  className = ''
}) => {
  const getStatusConfig = useMemo(() => {
    switch (status) {
      case 'connected':
        return {
          icon: Wifi,
          color: 'text-green-500',
          bgColor: 'bg-green-500',
          label: 'Connected',
          showReconnect: false
        };
      case 'connecting':
        return {
          icon: Wifi,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-500',
          label: 'Connecting...',
          showReconnect: false
        };
      case 'disconnected':
        return {
          icon: WifiOff,
          color: 'text-red-500',
          bgColor: 'bg-red-500',
          label: 'Disconnected',
          showReconnect: true
        };
      case 'error':
        return {
          icon: AlertTriangle,
          color: 'text-orange-500',
          bgColor: 'bg-orange-500',
          label: 'Connection Error',
          showReconnect: true
        };
      default:
        return {
          icon: WifiOff,
          color: 'text-gray-500',
          bgColor: 'bg-gray-500',
          label: 'Unknown',
          showReconnect: false
        };
    }
  }, [status]);

  const qualityColor = useMemo(() => {
    switch (connectionQuality) {
      case 'excellent':
        return 'text-green-600';
      case 'good':
        return 'text-yellow-600';
      case 'poor':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  }, [connectionQuality]);

  const formattedUptime = useMemo(() => {
    if (uptime < 60) return `${uptime}s`;
    if (uptime < 3600) return `${Math.floor(uptime / 60)}m`;
    if (uptime < 86400) return `${Math.floor(uptime / 3600)}h`;
    return `${Math.floor(uptime / 86400)}d`;
  }, [uptime]);

  const formattedLastUpdate = useMemo(() => {
    if (!lastUpdate) return 'Never';
    try {
      const date = new Date(lastUpdate);
      // An unparseable date yields NaN getTime() (no throw), which would fall
      // through to toLocaleTimeString() → "Invalid Date". Detect it explicitly.
      if (isNaN(date.getTime())) return 'Invalid time';
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSeconds = Math.floor(diffMs / 1000);

      if (diffSeconds < 60) return `${diffSeconds}s ago`;
      if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
      return date.toLocaleTimeString();
    } catch {
      return 'Invalid time';
    }
  }, [lastUpdate]);

  const handleReconnectClick = useCallback(() => {
    onReconnect?.();
  }, [onReconnect]);

  const config = getStatusConfig;
  const Icon = config.icon;

  return (
    <div className={`flex items-center gap-3 p-3 bg-white rounded-lg shadow-sm border ${className}`}>
      {/* Status Indicator */}
      <div className="relative">
        <div className={`w-3 h-3 rounded-full ${config.bgColor}`}>
          {status === 'connecting' && (
            <div className={`w-3 h-3 rounded-full ${config.bgColor} animate-pulse`}></div>
          )}
        </div>
      </div>

      {/* Connection Icon */}
      <Icon className={`w-5 h-5 ${config.color}`} />

      {/* Status Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900">{config.label}</span>
          {status === 'connected' && latency > 0 && (
            <span className={`text-sm ${qualityColor}`}>
              {latency}ms
            </span>
          )}
        </div>

        {status === 'connected' && (
          <div className="flex items-center gap-4 text-xs text-gray-500 mt-1">
            {clientCount > 0 && (
              <div className="flex items-center gap-1">
                <Users className="w-3 h-3" />
                <span>{clientCount} clients</span>
              </div>
            )}
            {uptime > 0 && (
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{formattedUptime} uptime</span>
              </div>
            )}
            {lastUpdate && (
              <span>Updated {formattedLastUpdate}</span>
            )}
          </div>
        )}
      </div>

      {/* Reconnect Button */}
      {config.showReconnect && onReconnect && (
        <button
          onClick={handleReconnectClick}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
          title="Reconnect"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Retry</span>
        </button>
      )}

      {/* Detailed Tooltip Info */}
      <div className="relative group">
        <button className="w-5 h-5 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-xs text-gray-600 transition-colors">
          ?
        </button>

        {/* Tooltip */}
        <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          <div className="space-y-1">
            <div>Status: <span className="font-medium">{config.label}</span></div>
            {status === 'connected' && (
              <>
                <div>Latency: <span className="font-medium">{latency}ms</span></div>
                <div>Quality: <span className="font-medium capitalize">{connectionQuality}</span></div>
                <div>Connected Clients: <span className="font-medium">{clientCount}</span></div>
                <div>Server Uptime: <span className="font-medium">{formattedUptime}</span></div>
                {lastUpdate && (
                  <div>Last Update: <span className="font-medium">{formattedLastUpdate}</span></div>
                )}
              </>
            )}
            {(status === 'disconnected' || status === 'error') && (
              <div className="text-yellow-200">
                Click retry to attempt reconnection
              </div>
            )}
          </div>

          {/* Tooltip Arrow */}
          <div className="absolute top-0 right-4 -mt-1 w-2 h-2 bg-gray-900 transform rotate-45"></div>
        </div>
      </div>
    </div>
  );
});
