using System;
using System.IO;
using System.Net.Http;

namespace HomeAura.AutoCAD.Agent
{
    internal sealed class HttpContentLimitExceededException :
        IOException
    {
        public HttpContentLimitExceededException()
            : base("HTTP response content exceeds the configured limit.")
        {
        }
    }

    internal static class BoundedHttpContentReader
    {
        public const int AnalysisResponseMaximumBytes =
            10 * 1024 * 1024;

        public static byte[] Read(
            HttpContent content,
            int maximumBytes)
        {
            if (content == null)
            {
                throw new ArgumentNullException("content");
            }

            if (maximumBytes <= 0)
            {
                throw new ArgumentOutOfRangeException(
                    "maximumBytes"
                );
            }

            long? declaredLength =
                content.Headers.ContentLength;
            if (declaredLength.HasValue &&
                declaredLength.Value > maximumBytes)
            {
                throw new HttpContentLimitExceededException();
            }

            using (Stream input =
                   content
                       .ReadAsStreamAsync()
                       .GetAwaiter()
                       .GetResult())
            using (MemoryStream output = new MemoryStream())
            {
                byte[] buffer = new byte[8192];
                int totalBytes = 0;

                while (true)
                {
                    int bytesRead = input.Read(
                        buffer,
                        0,
                        buffer.Length
                    );
                    if (bytesRead == 0)
                    {
                        break;
                    }

                    if (bytesRead > maximumBytes - totalBytes)
                    {
                        throw new HttpContentLimitExceededException();
                    }

                    output.Write(buffer, 0, bytesRead);
                    totalBytes += bytesRead;
                }

                return output.ToArray();
            }
        }
    }
}
