from abaqus import *
from abaqusConstants import *
import part
import sketch
import section
import material
import assembly
import step
import load
import mesh
import job
import sys

try:
    ler_texto = raw_input
except NameError:
    ler_texto = input


# Solicita um numero decimal positivo ao usuario pelo terminal, usando o valor padrao se nada for digitado.
def pedir_float(mensagem, padrao):
    while True:
        entrada = ler_texto("{} [{}]: ".format(mensagem, padrao)).strip()
        if entrada == "":
            return float(padrao)
        try:
            valor = float(entrada.replace(",", "."))
            if valor <= 0.0:
                print("  -> Erro: o valor deve ser maior que zero.")
                continue
            return valor
        except ValueError:
            print("  -> Erro: digite um numero valido.")


# Solicita um numero inteiro maior ou igual a 1 ao usuario pelo terminal, usando o valor padrao se nada for digitado.
def pedir_int(mensagem, padrao):
    while True:
        entrada = ler_texto("{} [{}]: ".format(mensagem, padrao)).strip()
        if entrada == "":
            return int(padrao)
        try:
            valor = int(entrada)
            if valor < 1:
                print("  -> Erro: a quantidade deve ser pelo menos 1.")
                continue
            return valor
        except ValueError:
            print("  -> Erro: digite um numero inteiro valido.")


# Gera uma matriz padrao alternando 0 (frio) e 1 (quente) conforme o numero de colunas e linhas.
def gerar_matriz_padrao(furos_na_linha, furos_na_coluna):
    matriz = []
    indice = 0
    for _ in range(furos_na_coluna):
        linha = []
        for _ in range(furos_na_linha):
            linha.append(indice % 2)
            indice += 1
        matriz.append(linha)
    return matriz


# Converte uma linha de texto digitada pelo usuario em uma lista de inteiros 0 e 1 validada pelo tamanho esperado.
def interpretar_linha_matriz(texto, tamanho_esperado):
    limpo = texto.replace(",", " ").replace("[", " ").replace("]", " ").strip()
    partes = limpo.split()
    if len(partes) == 1 and len(partes[0]) == tamanho_esperado and all(c in ('0', '1') for c in partes[0]):
        return [int(c) for c in partes[0]]

    if len(partes) != tamanho_esperado:
        raise ValueError("A linha deve conter exatamente {} valores (0 ou 1).".format(tamanho_esperado))

    valores = []
    for p in partes:
        if p not in ('0', '1'):
            raise ValueError("Use apenas 0 (frio) ou 1 (quente).")
        valores.append(int(p))
    return valores


# Verifica se as dimensoes do bloco, a quantidade de tubos, o raio e a matriz de secoes sao validos.
def validar_geometria(largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo, matriz_secoes=None):
    if largura <= 0.0 or altura <= 0.0 or comprimento <= 0.0:
        return "As dimensoes do bloco devem ser maiores que zero."
    if furos_na_linha < 1 or furos_na_coluna < 1:
        return "A quantidade de tubos na linha e na coluna deve ser pelo menos 1."
    if raio_tubo <= 0.0:
        return "O raio do tubo deve ser maior que zero."

    diametro_tubo = 2.0 * raio_tubo
    if furos_na_linha * diametro_tubo >= largura:
        return "{} tubos de diametro {:.4f} (total {:.4f}) nao cabem na largura {:.4f}.".format(
            furos_na_linha, diametro_tubo, furos_na_linha * diametro_tubo, largura
        )
    if furos_na_coluna * diametro_tubo >= altura:
        return "{} tubos de diametro {:.4f} (total {:.4f}) nao cabem na altura {:.4f}.".format(
            furos_na_coluna, diametro_tubo, furos_na_coluna * diametro_tubo, altura
        )

    if matriz_secoes is not None:
        if len(matriz_secoes) != furos_na_coluna:
            return "A matriz deve ter {} linhas (tubos na coluna).".format(furos_na_coluna)
        for linha in matriz_secoes:
            if len(linha) != furos_na_linha:
                return "Cada linha da matriz deve ter {} colunas (tubos na linha).".format(furos_na_linha)
            for valor in linha:
                if valor not in (0, 1):
                    return "A matriz deve conter apenas 0 (frio) ou 1 (quente)."

    return None


# Coleta e valida os parametros geometricos e a matriz de secoes (0 = frio, 1 = quente) pelo terminal.
def obter_parametros_terminal():
    print("\n" + "=" * 60)
    print("PARAMETROS DO BLOCO PARTICIONADO (Enter = valor padrao)")
    print("=" * 60)

    while True:
        largura = pedir_float("Largura do bloco (eixo X)", 1.0)
        altura = pedir_float("Altura do bloco (eixo Y)", 1.0)
        comprimento = pedir_float("Comprimento/profundidade do bloco (eixo Z)", 10.0)
        furos_na_linha = pedir_int("Quantidade de tubos na linha (horizontal / eixo X)", 3)
        furos_na_coluna = pedir_int("Quantidade de tubos na coluna (vertical / eixo Y)", 3)
        raio_tubo = pedir_float("Raio de cada tubo", 0.1)

        erro = validar_geometria(
            largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo
        )
        if erro:
            print("\n[AVISO] {}\nInforme os valores novamente.\n".format(erro))
            continue

        print("\nMatriz de secoes dos tubos (0 = frio, 1 = quente):")
        print("Digite {} valores por linha separados por espaco (de cima para baixo).".format(furos_na_linha))
        matriz_padrao = gerar_matriz_padrao(furos_na_linha, furos_na_coluna)
        matriz_secoes = []

        for idx in range(furos_na_coluna):
            padrao_str = " ".join(str(v) for v in matriz_padrao[idx])
            while True:
                entrada = ler_texto("  Linha {} [{}]: ".format(idx + 1, padrao_str)).strip()
                if entrada == "":
                    matriz_secoes.append(matriz_padrao[idx])
                    break
                try:
                    linha_valores = interpretar_linha_matriz(entrada, furos_na_linha)
                    matriz_secoes.append(linha_valores)
                    break
                except ValueError as e:
                    print("  -> Erro: {}".format(e))

        return largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo, matriz_secoes


# Coleta e valida os parametros geometricos e a matriz de secoes por caixas de dialogo do Abaqus/CAE.
def obter_parametros_cae():
    valores = [
        '1.0',
        '1.0',
        '10.0',
        '3',
        '3',
        '0.1',
    ]
    aviso = 'Informe os parametros geometricos do bloco:'

    while True:
        campos = (
            ('Largura do bloco (eixo X):', valores[0]),
            ('Altura do bloco (eixo Y):', valores[1]),
            ('Comprimento/profundidade (eixo Z):', valores[2]),
            ('Tubos na linha (horizontal / X):', valores[3]),
            ('Tubos na coluna (vertical / Y):', valores[4]),
            ('Raio de cada tubo:', valores[5]),
        )
        res = getInputs(
            fields=campos,
            label=aviso,
            dialogTitle='Parametros do Bloco Particionado'
        )
        if res is None:
            return None

        valores = list(res)
        try:
            largura = float(res[0].replace(",", "."))
            altura = float(res[1].replace(",", "."))
            comprimento = float(res[2].replace(",", "."))
            furos_na_linha = int(res[3])
            furos_na_coluna = int(res[4])
            raio_tubo = float(res[5].replace(",", "."))
        except ValueError:
            aviso = 'Erro de formato: digite apenas numeros validos.'
            continue

        erro = validar_geometria(
            largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo
        )
        if erro:
            aviso = 'ERRO: ' + erro
            continue

        break

    matriz_padrao = gerar_matriz_padrao(furos_na_linha, furos_na_coluna)
    linhas_texto = [" ".join(str(v) for v in linha) for linha in matriz_padrao]
    aviso_matriz = 'Matriz de secoes (0 = frio, 1 = quente) - {} valores por linha:'.format(furos_na_linha)

    while True:
        campos_matriz = tuple(
            ('Linha {} (de cima para baixo):'.format(i + 1), linhas_texto[i])
            for i in range(furos_na_coluna)
        )
        res_matriz = getInputs(
            fields=campos_matriz,
            label=aviso_matriz,
            dialogTitle='Matriz de Secoes (0 = Frio, 1 = Quente)'
        )
        if res_matriz is None:
            return None

        linhas_texto = list(res_matriz)
        try:
            matriz_secoes = [
                interpretar_linha_matriz(res_matriz[i], furos_na_linha)
                for i in range(furos_na_coluna)
            ]
            return largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo, matriz_secoes
        except ValueError as e:
            aviso_matriz = 'ERRO: ' + str(e)


# Cria os materiais (FluidoFrio, FluidoQuente e Solido) e suas respectivas secoes solidas homogeneas no modelo.
def criar_materiais_e_secoes(modelo):
    mat_frio = modelo.Material(name='FluidoFrio')
    mat_frio.Conductivity(table=((0.06, ), ))
    mat_frio.Density(table=((163.0, ), ))
    mat_frio.SpecificHeat(table=((1258.0, ), ))

    mat_quente = modelo.Material(name='FluidoQuente')
    mat_quente.Conductivity(table=((0.05, ), ))
    mat_quente.Density(table=((54.0, ), ))
    mat_quente.SpecificHeat(table=((1120.0, ), ))

    mat_solido = modelo.Material(name='Solido')
    mat_solido.Conductivity(table=((205.0, ), ))
    mat_solido.Density(table=((2700.0, ), ))
    mat_solido.SpecificHeat(table=((900.0, ), ))

    modelo.HomogeneousSolidSection(name='Sec_FluidoFrio', material='FluidoFrio', thickness=None)
    modelo.HomogeneousSolidSection(name='Sec_FluidoQuente', material='FluidoQuente', thickness=None)
    modelo.HomogeneousSolidSection(name='Sec_Solido', material='Solido', thickness=None)


# Atribui a secao solida a matriz e aplica Sec_FluidoFrio (0) ou Sec_FluidoQuente (1) conforme a matriz informada.
def atribuir_secoes(peca, matriz_secoes):
    peca.SectionAssignment(
        region=peca.sets['Set_Matriz'],
        sectionName='Sec_Solido',
        offset=0.0,
        offsetType=MIDDLE_SURFACE,
        offsetField='',
        thicknessAssignment=FROM_SECTION
    )

    indice = 1
    for linha in matriz_secoes:
        for valor in linha:
            nome_secao = 'Sec_FluidoFrio' if valor == 0 else 'Sec_FluidoQuente'
            peca.SectionAssignment(
                region=peca.sets['Set_Tubo_{}'.format(indice)],
                sectionName=nome_secao,
                offset=0.0,
                offsetType=MIDDLE_SURFACE,
                offsetField='',
                thicknessAssignment=FROM_SECTION
            )
            indice += 1


# Gera a malha termica 3D (elementos DC3D8, DC3D6 e DC3D4) na peca particionada.
def gerar_malha(peca, raio_tubo, espaco_x, espaco_y, comprimento):
    tamanho_malha = min(raio_tubo * 0.8, espaco_x * 0.9, espaco_y * 0.9, comprimento / 10.0)
    peca.seedPart(size=tamanho_malha, deviationFactor=0.1, minSizeFactor=0.1)

    if comprimento / tamanho_malha > 25.0:
        arestas_z = [
            aresta for aresta in peca.edges
            if 0.01 * comprimento < aresta.pointOn[0][2] < 0.99 * comprimento
        ]
        if arestas_z:
            peca.seedEdgeByNumber(edges=arestas_z, number=25, constraint=FIXED)

    elem_hex = mesh.ElemType(elemCode=DC3D8, elemLibrary=STANDARD)
    elem_wedge = mesh.ElemType(elemCode=DC3D6, elemLibrary=STANDARD)
    elem_tet = mesh.ElemType(elemCode=DC3D4, elemLibrary=STANDARD)

    peca.setElementType(regions=(peca.cells,), elemTypes=(elem_hex, elem_wedge, elem_tet))
    peca.setMeshControls(regions=peca.cells, elemShape=HEX_DOMINATED, technique=SWEEP)
    peca.generateMesh()


# Cria a instancia, o step TransferenciaDeCalor, atualiza o Field Output (HFL, NT, TEMP) e aplica as condicoes de contorno termicas.
def configurar_transferencia_calor(modelo, peca, centros_x, centros_y, comprimento, matriz_secoes):
    coords_quentes_esq = []
    coords_frias_dir = []

    for j, cy in enumerate(reversed(centros_y)):
        for i, cx in enumerate(centros_x):
            if matriz_secoes[j][i] == 1:
                coords_quentes_esq.append(((cx, cy, comprimento),))
            else:
                coords_frias_dir.append(((cx, cy, 0.0),))

    if coords_quentes_esq:
        faces_quentes_esq = peca.faces.findAt(*coords_quentes_esq)
        peca.Set(faces=faces_quentes_esq, name='Set_Faces_Quentes_Esq')

    if coords_frias_dir:
        faces_frias_dir = peca.faces.findAt(*coords_frias_dir)
        peca.Set(faces=faces_frias_dir, name='Set_Faces_Frias_Dir')

    raiz_assembly = modelo.rootAssembly
    raiz_assembly.DatumCsysByDefault(CARTESIAN)
    instancia = raiz_assembly.Instance(
        name='Instancia_Bloco',
        part=peca,
        dependent=ON
    )

    modelo.HeatTransferStep(
        name='TransferenciaDeCalor',
        previous='Initial',
        response=STEADY_STATE
    )

    if 'F-Output-1' in modelo.fieldOutputRequests.keys():
        modelo.fieldOutputRequests['F-Output-1'].setValues(
            variables=('HFL', 'NT', 'TEMP')
        )
    else:
        modelo.FieldOutputRequest(
            name='F-Output-1',
            createStepName='TransferenciaDeCalor',
            variables=('HFL', 'NT', 'TEMP')
        )

    if coords_quentes_esq:
        modelo.TemperatureBC(
            name='BC_Tubos_Quentes_Esq',
            createStepName='TransferenciaDeCalor',
            region=instancia.sets['Set_Faces_Quentes_Esq'],
            fixed=OFF,
            distributionType=UNIFORM,
            fieldName='',
            magnitude=100.0,
            amplitude=UNSET
        )

    if coords_frias_dir:
        modelo.TemperatureBC(
            name='BC_Tubos_Frios_Dir',
            createStepName='TransferenciaDeCalor',
            region=instancia.sets['Set_Faces_Frias_Dir'],
            fixed=OFF,
            distributionType=UNIFORM,
            fieldName='',
            magnitude=0.0,
            amplitude=UNSET
        )


# Cria o job de simulacao termica, submete para execucao, aguarda a conclusao e abre o arquivo de resultados (.odb).
def criar_e_executar_job(nome_modelo, nome_job='Job_TransferenciaDeCalor'):
    print("\nSubmetendo e executando o job '{}'...".format(nome_job))
    mdb.Job(
        name=nome_job,
        model=nome_modelo,
        description='Analise de transferencia de calor',
        type=ANALYSIS,
        atTime=None,
        waitMinutes=0,
        waitHours=0,
        queue=None,
        memory=90,
        memoryUnits=PERCENTAGE,
        getMemoryFromAnalysis=True,
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        echoPrint=OFF,
        modelPrint=OFF,
        contactPrint=OFF,
        historyPrint=OFF,
        userSubroutine='',
        scratch='',
        resultsFormat=ODB
    )
    mdb.jobs[nome_job].submit(consistencyChecking=OFF)
    mdb.jobs[nome_job].waitForCompletion()
    print("Job '{}' finalizado com sucesso!".format(nome_job))

    try:
        import visualization
        odb = session.openOdb(name=nome_job + '.odb')
        vp = session.viewports[session.currentViewportName]
        vp.setValues(displayedObject=odb)
        vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF, ))
    except Exception:
        pass


# Cria o bloco solido, particiona os cilindros, atribui secoes, gera a malha, configura o step termico e executa o job.
def criar_bloco_particionado(
    largura=1.0,
    altura=1.0,
    comprimento=10.0,
    furos_na_linha=3,
    furos_na_coluna=3,
    raio_tubo=0.1,
    matriz_secoes=None,
    nome_modelo='Model-1',
    nome_peca='Bloco_Particionado'
):
    if matriz_secoes is None:
        matriz_secoes = gerar_matriz_padrao(furos_na_linha, furos_na_coluna)

    erro = validar_geometria(
        largura, altura, comprimento, furos_na_linha, furos_na_coluna, raio_tubo, matriz_secoes
    )
    if erro:
        raise ValueError(erro)

    diametro_tubo = 2.0 * raio_tubo

    espaco_x = (largura - furos_na_linha * diametro_tubo) / float(furos_na_linha + 1)
    espaco_y = (altura - furos_na_coluna * diametro_tubo) / float(furos_na_coluna + 1)

    centros_x = [espaco_x + raio_tubo + i * (diametro_tubo + espaco_x) for i in range(furos_na_linha)]
    centros_y = [espaco_y + raio_tubo + j * (diametro_tubo + espaco_y) for j in range(furos_na_coluna)]

    ponto_matriz = (espaco_x / 2.0, espaco_y / 2.0, comprimento / 2.0)

    print("\nGerando geometria e particionando celulas...")

    if nome_modelo in mdb.models.keys():
        modelo = mdb.models[nome_modelo]
    else:
        modelo = mdb.Model(name=nome_modelo)

    s_base = modelo.ConstrainedSketch(
        name='__profile_base__',
        sheetSize=max(largura, altura) * 4.0
    )
    s_base.rectangle(point1=(0.0, 0.0), point2=(largura, altura))

    peca = modelo.Part(
        name=nome_peca,
        dimensionality=THREE_D,
        type=DEFORMABLE_BODY
    )
    peca.BaseSolidExtrude(sketch=s_base, depth=comprimento)
    del modelo.sketches['__profile_base__']

    face_frontal = peca.faces.findAt(((largura / 2.0, altura / 2.0, comprimento),),)
    aresta_superior = peca.edges.findAt(((largura / 2.0, altura, comprimento),),)

    transformacao = peca.MakeSketchTransform(
        sketchPlane=face_frontal[0],
        sketchUpEdge=aresta_superior[0],
        sketchPlaneSide=SIDE1,
        sketchOrientation=TOP,
        origin=(0.0, 0.0, comprimento)
    )

    s_part = modelo.ConstrainedSketch(
        name='__profile_part__',
        sheetSize=max(largura, altura) * 4.0,
        transform=transformacao
    )
    peca.projectReferencesOntoSketch(sketch=s_part, filter=COPLANAR_EDGES)

    for cx in centros_x:
        for cy in centros_y:
            s_part.CircleByCenterPerimeter(
                center=(cx, cy),
                point1=(cx + raio_tubo, cy)
            )

    peca.PartitionFaceBySketch(
        faces=face_frontal,
        sketch=s_part
    )
    del modelo.sketches['__profile_part__']

    eixo_extrude = peca.DatumAxisByTwoPoint(
        point1=(0.0, 0.0, comprimento),
        point2=(0.0, 0.0, 0.0)
    )

    for cx in centros_x:
        for cy in centros_y:
            celula_matriz = peca.cells.findAt((ponto_matriz,),)
            face_circulo = peca.faces.findAt(((cx, cy, comprimento),),)
            arestas_circulo = tuple(peca.edges[i] for i in face_circulo[0].getEdges())

            peca.PartitionCellByExtrudeEdge(
                line=peca.datums[eixo_extrude.id],
                cells=celula_matriz,
                edges=arestas_circulo,
                sense=FORWARD
            )

    celula_matriz = peca.cells.findAt((ponto_matriz,),)
    peca.Set(cells=celula_matriz, name='Set_Matriz')

    coords_celulas_tubos = []
    indice = 1
    for cy in reversed(centros_y):
        for cx in centros_x:
            pt = ((cx, cy, comprimento / 2.0),)
            coords_celulas_tubos.append(pt)
            cel_ind = peca.cells.findAt(pt,)
            peca.Set(cells=cel_ind, name='Set_Tubo_{}'.format(indice))
            indice += 1

    celulas_todos_tubos = peca.cells.findAt(*coords_celulas_tubos)
    peca.Set(cells=celulas_todos_tubos, name='Set_Todos_Tubos')

    criar_materiais_e_secoes(modelo)
    atribuir_secoes(peca, matriz_secoes)
    gerar_malha(peca, raio_tubo, espaco_x, espaco_y, comprimento)
    configurar_transferencia_calor(modelo, peca, centros_x, centros_y, comprimento, matriz_secoes)
    criar_e_executar_job(nome_modelo)

    return peca


if __name__ == '__main__':
    try:
        params = obter_parametros_terminal()
    except (EOFError, SystemError):
        params = obter_parametros_cae()

    if params is not None:
        criar_bloco_particionado(*params)