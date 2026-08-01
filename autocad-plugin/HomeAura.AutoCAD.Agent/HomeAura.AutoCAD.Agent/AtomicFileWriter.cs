using System;
using System.IO;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AtomicFileWriter
    {
        public static void PublishHistoryThenCurrent(
            string historyPath,
            string currentPath,
            Action<string> publisher)
        {
            if (string.IsNullOrWhiteSpace(historyPath))
            {
                throw new ArgumentException(
                    "History path is required.",
                    "historyPath"
                );
            }

            if (string.IsNullOrWhiteSpace(currentPath))
            {
                throw new ArgumentException(
                    "Current path is required.",
                    "currentPath"
                );
            }

            if (publisher == null)
            {
                throw new ArgumentNullException("publisher");
            }

            publisher(historyPath);
            publisher(currentPath);
        }

        public static void Write(
            string path,
            Action<Stream> writer)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                throw new ArgumentException(
                    "Destination path is required.",
                    "path"
                );
            }

            if (writer == null)
            {
                throw new ArgumentNullException("writer");
            }

            string destinationPath = Path.GetFullPath(path);
            string directory =
                Path.GetDirectoryName(destinationPath);

            if (string.IsNullOrWhiteSpace(directory))
            {
                throw new InvalidOperationException(
                    "Destination directory is unavailable."
                );
            }

            string temporaryPath = Path.Combine(
                directory,
                "." + Path.GetFileName(destinationPath) +
                "." + Guid.NewGuid().ToString("N") +
                ".tmp"
            );

            try
            {
                using (FileStream stream =
                       new FileStream(
                           temporaryPath,
                           FileMode.CreateNew,
                           FileAccess.Write,
                           FileShare.None))
                {
                    writer(stream);
                    stream.Flush(true);
                }

                if (File.Exists(destinationPath))
                {
                    File.Replace(
                        temporaryPath,
                        destinationPath,
                        null
                    );
                }
                else
                {
                    File.Move(
                        temporaryPath,
                        destinationPath
                    );
                }
            }
            finally
            {
                if (File.Exists(temporaryPath))
                {
                    File.Delete(temporaryPath);
                }
            }
        }
    }
}
