"""Forward the frozen endpoint 127.0.0.1:18090 inside the Linux container to the native
macOS llama-server (host loopback, reached from the Lima VM as host.lima.internal:18090).
Byte-level TCP relay; does not inspect or alter requests or responses."""
import asyncio, sys
TARGET = (sys.argv[1] if len(sys.argv) > 1 else 'host.lima.internal', 18090)

async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data); await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()

async def handle(client_reader, client_writer):
    try:
        server_reader, server_writer = await asyncio.open_connection(*TARGET)
    except OSError:
        client_writer.close(); return
    await asyncio.gather(pipe(client_reader, server_writer), pipe(server_reader, client_writer))

async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 18090)
    async with server:
        await server.serve_forever()

asyncio.run(main())
