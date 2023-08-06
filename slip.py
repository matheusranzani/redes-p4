class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.escape = False
        self.buffer_quadro = bytearray()

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # Substitui os bytes especiais no datagrama
        datagrama = datagrama.replace(b'\xDB', b'\xDB\xDD')
        datagrama = datagrama.replace(b'\xC0', b'\xDB\xDC')

        # Adiciona o byte de início do datagrama
        datagrama = b'\xC0' + datagrama + b'\xC0'

        # Envia o datagrama encapsulado pela linha serial
        self.linha_serial.enviar(datagrama)

    def __raw_recv(self, dados):
        # Processa os dados recebidos
        for byte in dados:
            try:
                if self.escape:
                    if byte == 0xDC:
                        self.buffer_quadro.append(0xC0)
                    elif byte == 0xDD:
                        self.buffer_quadro.append(0xDB)
                    else:
                        # Byte de escape inválido, descarta e reinicia
                        self.escape = False
                        self.buffer_quadro.clear()
                    self.escape = False
                elif byte == 0xC0:
                    # Fim de quadro, processa o datagrama
                    if self.buffer_quadro:
                        datagrama = bytes(self.buffer_quadro)
                        self.callback(datagrama)
                    self.buffer_quadro.clear()
                elif byte == 0xDB:
                    self.escape = True
                else:
                    self.buffer_quadro.append(byte)
            except:
                # Ignora exceção, mas mostra na tela
                import traceback
                traceback.print_exc()
                self.escape = False
                self.buffer_quadro.clear()
            finally:
                # Descarta datagramas vazios da fila
                self.linha_serial.fila = self.linha_serial.fila.replace(b'\xC0\xC0', b'\xC0')
