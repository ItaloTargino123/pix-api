"""
Cenários testados:
1. Coleta simples (1 mensagem por vez)
2. Coleta multipart (até 10 mensagens)
3. Limite de 6 streams por ISPB
4. Long polling (8s timeout)
5. Mensagens não duplicadas entre streams

Para Executar:
    locust -f locustfile.py --host=http://localhost:8000
"""

import random
import string
from locust import HttpUser, task, between, events
from collections import defaultdict
import threading


# Métricas customizadas
collected_messages = defaultdict(set)
duplicate_count = 0
lock = threading.Lock()


def generate_ispb():
    """Gera ISPB aleatório de 8 dígitos."""
    return ''.join(random.choices(string.digits, k=8))


class PixCollector(HttpUser):
    
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        """Setup inicial - gera mensagens para o ISPB."""
        self.ispb = generate_ispb()
        self.stream_id = None
        
        # Gera mensagens para coleta
        self.client.post(
            f"/api/pix/util/msgs/{self.ispb}/20/",
            name="/api/pix/util/msgs/[ispb]/[n]/"
        )
    
    @task(10)
    def collect_single(self):
        """Coleta mensagens uma por vez (application/json)."""
        self._collect_messages(multipart=False)
    
    @task(5)
    def collect_multipart(self):
        """Coleta múltiplas mensagens (multipart/json)."""
        self._collect_messages(multipart=True)
    
    def _collect_messages(self, multipart=False):
        """Fluxo completo de coleta."""
        global duplicate_count
        
        headers = {"Accept": "multipart/json"} if multipart else {}
        
        # 1. Inicia stream
        with self.client.get(
            f"/api/pix/{self.ispb}/stream/start",
            headers=headers,
            name="/api/pix/[ispb]/stream/start",
            catch_response=True
        ) as response:
            
            if response.status_code == 429:
                response.success()  # Limite atingido é esperado
                return
            
            if response.status_code == 204:
                response.success()  # Sem mensagens
                return
            
            if response.status_code != 200:
                response.failure(f"Unexpected status: {response.status_code}")
                return
            
            pull_next = response.headers.get("Pull-Next")
            if not pull_next:
                response.failure("Missing Pull-Next header")
                return
            
            # Verifica duplicatas
            data = response.json()
            messages = data if isinstance(data, list) else [data]
            
            with lock:
                for msg in messages:
                    end_to_end_id = msg.get("endToEndId")
                    if end_to_end_id in collected_messages[self.ispb]:
                        duplicate_count += 1
                    collected_messages[self.ispb].add(end_to_end_id)
        
        # 2. Continua polling (até 3 iterações)
        for _ in range(3):
            with self.client.get(
                pull_next,
                headers=headers,
                name="/api/pix/[ispb]/stream/[id]",
                catch_response=True
            ) as response:
                
                if response.status_code == 204:
                    response.success()
                    break
                
                if response.status_code == 200:
                    pull_next = response.headers.get("Pull-Next", pull_next)
                    
                    # Verifica duplicatas
                    data = response.json()
                    messages = data if isinstance(data, list) else [data]
                    
                    with lock:
                        for msg in messages:
                            end_to_end_id = msg.get("endToEndId")
                            if end_to_end_id in collected_messages[self.ispb]:
                                duplicate_count += 1
                            collected_messages[self.ispb].add(end_to_end_id)
                else:
                    response.failure(f"Unexpected status: {response.status_code}")
                    break
        
        # 3. Fecha stream
        self.client.delete(
            pull_next,
            name="/api/pix/[ispb]/stream/[id] (DELETE)"
        )


class StreamLimitTester(HttpUser):
    
    wait_time = between(1, 2)
    weight = 1  # Menos frequente que PixCollector
    
    def on_start(self):
        self.ispb = "99999999"  # ISPB fixo para testar limite
        
        # Gera mensagens
        self.client.post(
            f"/api/pix/util/msgs/{self.ispb}/50/",
            name="/api/pix/util/msgs/[ispb]/[n]/"
        )
    
    @task
    def test_stream_limit(self):
        streams = []
        exceeded_limit = False
        
        # Tenta abrir 8 streams
        for i in range(8):
            response = self.client.get(
                f"/api/pix/{self.ispb}/stream/start",
                name="/api/pix/[ispb]/stream/start (limit test)",
                catch_response=True
            )
            
            if response.status_code == 429:
                exceeded_limit = True
                response.success()
                break
            elif response.status_code in [200, 204]:
                pull_next = response.headers.get("Pull-Next")
                if pull_next:
                    streams.append(pull_next)
                response.success()
            else:
                response.failure(f"Unexpected: {response.status_code}")
        
        # Fecha todos os streams abertos
        for stream_url in streams:
            self.client.delete(
                stream_url,
                name="/api/pix/[ispb]/stream/[id] (DELETE cleanup)"
            )


class LongPollingTester(HttpUser):
    
    wait_time = between(5, 10)
    weight = 1
    
    def on_start(self):
        self.ispb = "00000001"
    
    @task
    def test_long_polling(self):
        with self.client.get(
            f"/api/pix/{self.ispb}/stream/start",
            name="/api/pix/[ispb]/stream/start (long poll)",
            catch_response=True,
            timeout=15
        ) as response:
            
            if response.status_code == 204:
                # Verifica se demorou pelo menos 7 segundos
                if response.elapsed.total_seconds() >= 7:
                    response.success()
                else:
                    response.failure(
                        f"Long polling muito rápido: {response.elapsed.total_seconds():.2f}s"
                    )
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected: {response.status_code}")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    print("\n" + "=" * 60)
    print("RELATÓRIO DE LOAD TEST")
    print("=" * 60)
    
    total_messages = sum(len(msgs) for msgs in collected_messages.values())
    print(f"Total de mensagens coletadas: {total_messages}")
    print(f"ISPBs diferentes: {len(collected_messages)}")
    print(f"Mensagens duplicadas: {duplicate_count}")
    
    if duplicate_count > 0:
        print("\n⚠️  ALERTA: Foram encontradas mensagens duplicadas!")
    else:
        print("\n✅ Nenhuma mensagem duplicada encontrada")
    
    print("=" * 60)
