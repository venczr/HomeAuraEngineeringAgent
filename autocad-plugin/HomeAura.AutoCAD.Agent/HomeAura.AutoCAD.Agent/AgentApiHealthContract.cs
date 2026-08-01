using System;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Xml;

namespace HomeAura.AutoCAD.Agent
{
    internal static class AgentApiHealthContract
    {
        public const int MaximumResponseBytes = 4096;

        private const string ExpectedStatus = "ok";
        private const string ExpectedService =
            "HomeAura Engineering Agent API";

        public static bool IsExpected(byte[] payload)
        {
            if (payload == null ||
                payload.Length == 0 ||
                payload.Length > MaximumResponseBytes)
            {
                return false;
            }

            try
            {
                HealthResponse response;

                using (MemoryStream stream =
                       new MemoryStream(payload, false))
                {
                    DataContractJsonSerializer serializer =
                        new DataContractJsonSerializer(
                            typeof(HealthResponse)
                        );

                    response =
                        serializer.ReadObject(stream)
                            as HealthResponse;
                }

                return
                    response != null &&
                    string.Equals(
                        response.Status,
                        ExpectedStatus,
                        StringComparison.Ordinal
                    ) &&
                    string.Equals(
                        response.Service,
                        ExpectedService,
                        StringComparison.Ordinal
                    );
            }
            catch (SerializationException)
            {
                return false;
            }
            catch (XmlException)
            {
                return false;
            }
            catch (InvalidOperationException)
            {
                return false;
            }
        }

        [DataContract]
        private sealed class HealthResponse
        {
            [DataMember(Name = "status")]
            public string Status { get; set; }

            [DataMember(Name = "service")]
            public string Service { get; set; }
        }
    }
}
