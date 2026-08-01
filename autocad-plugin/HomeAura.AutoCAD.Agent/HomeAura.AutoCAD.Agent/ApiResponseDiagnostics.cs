using System;
using System.Globalization;
using System.Net;

namespace HomeAura.AutoCAD.Agent
{
    internal static class ApiResponseDiagnostics
    {
        public static string FormatFailure(
            HttpStatusCode statusCode)
        {
            string statusName;

            switch ((int)statusCode)
            {
                case 422:
                    statusName = "UnprocessableEntity";
                    break;
                case 429:
                    statusName = "TooManyRequests";
                    break;
                default:
                    statusName = Enum.GetName(
                        typeof(HttpStatusCode),
                        statusCode
                    );
                    break;
            }

            if (string.IsNullOrWhiteSpace(statusName))
            {
                statusName = "UnknownStatus";
            }

            return "HomeAura API вернул ошибку " +
                ((int)statusCode).ToString(
                    CultureInfo.InvariantCulture
                ) +
                " " + statusName +
                ". Диагностическое тело ответа скрыто.";
        }
    }
}
