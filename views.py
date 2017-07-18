class ApiPUCPersonaView(AuthSesion, APIView):
    """
        Retorna los datos de las personas existentes en el sistema de empleados del sistema de nóminn
        con los siguientes criterios de busqueda:
            *"puc_persona_id" para buscar el id de PUC del empleado;
            *"puc_curp" para buscar el empleado con su CURP;
            *"puc_rfc" para buscar el empleado con su RFC;
            *"puc_nombre" para buscar el empleado con su NOMBRE COMPLETO(nombre apellido paterno apellido materno);
            Retorna si el empleado ya tiene un plaza o contrato en activo solo si es enviado alguno de los siguientes parametros:
            """

    def get(self, request):
        puc_persona_id = self.request.GET.get("puc_persona_id")
        puc_curp = self.request.GET.get("puc_curp")
        puc_rfc = self.request.GET.get("puc_rfc")
        puc_nombre = self.request.GET.get("puc_nombre")

        if not puc_nombre and not puc_rfc and not puc_curp and not puc_persona_id:
            error_msj = {"msj": "No se han recibido ninguno de los parametros de busqueda establecidos."}
            respuesta = Response(error_msj)
            respuesta.status_code = 500
            return respuesta

        respuesta = None
        r = None
        id = 0
        plazas_lista = []
        lista_persona = []

        headers = {"Authorization": settings.TOKEN_EMPLEADO}
        if puc_nombre:
            param = {'puc_nombre': puc_nombre.upper()}
            r = requests.get(settings.EMPLEADO + '/api/extplazasempleado/lista/?rpp=10', params=param, headers=headers)

        if puc_curp:
            param = {'puc_curp': puc_curp}
            r = requests.get(settings.EMPLEADO + '/api/extplazasempleado/lista/', params=param, headers=headers)

        if puc_rfc:
            param = {'puc_rfc': puc_rfc}
            r = requests.get(settings.EMPLEADO + '/api/extplazasempleado/lista/', params=param, headers=headers)

        if r.status_code == 200:
            respuesta = r.json()
            print(respuesta)
            if respuesta:
                for p in respuesta:
                    if p['plazas']:
                        plazas = p['plazas']
                        plazas_lista = []
                        for t in plazas:
                            plazas_lista.append(
                                {'unidad': t['u_admin']['text'], 'dependencia': t['u_admin']['padre_text']})
                            id = t['empleado']
                    else:
                        plazas_lista = []
                        id = 0
                    lista_persona.append({
                        'id': id,
                        'value': p['empleado']['nombre'].upper() + ' ' + p['empleado'][
                            'apellido_paterno'].upper() + ' ' + p['empleado']['apellido_materno'].upper(),
                        'label': p['empleado']['nombre'].upper() + ' ' + p['empleado'][
                            'apellido_paterno'].upper() + ' ' + p['empleado']['apellido_materno'].upper() + ' - ' +
                                 p['empleado']['curp'].upper(),
                        'nombre': p['empleado']['nombre'].upper() + ' ' + p['empleado'][
                            'apellido_paterno'].upper() + ' ' + p['empleado']['apellido_materno'].upper(),
                        'curp': p['empleado']['curp'],
                        'rfc': p['empleado']['rfc'],
                        'fecha_nacimiento': p['empleado']['fecha_nacimiento'],
                        'genero': p['empleado']['genero'],
                        'plaza': plazas_lista
                    })
            respuesta = lista_persona
        elif r.status_code == 403:
            respuesta = r.json
        else:
            respuesta = list()
        return Response(respuesta)


class reportePolizaView(LoginRequiredMixin, NeverCacheMixin, View):
    def get(self, request):
        """Se reciben los parametros desde el template"""
        periodo = self.request.GET.get('periodo')
        cat_anio_fiscal = self.request.GET.get('cat_anio_fiscal')
        dependencia = self.request.GET.get('dependencia')
        tipo_nomina = self.request.GET.get('tipo_nomina')
        organismo = self.request.GET.get('organismo')
        excluir = self.request.GET.getlist('excluir')
        excluir_list = list()
        nomina_text = Cat_tipo_nomina.objects.get(id=tipo_nomina)
        periodo_text = Cat_periodo.objects.get(id=periodo)
        contadorEncabezado = 0
        contadorDetalle = 0


        """
        Si alguno de los siguientes parametros llega vacio se le asigna el valor None para enviarlos a la función SQL
        """
        if dependencia == '':
            dependencia = None
        if organismo == '':
            organismo = None
        if excluir == '':
            excluir_list = None
        if dependencia:
            dpndncia = Cat_dependencias.objects.get(padre_id=0, id=dependencia)
            organismo = dpndncia.cat_tipo_organismo_id
        else:
            for dep in excluir:
                if dep:
                    excluir_list.append(int(dep))

        try:
            dependencia_text = Cat_dependencias.objects.get(padre_id=0, id=dependencia)
            dep= dependencia_text.clave
        except Cat_dependencias.DoesNotExist:
            if organismo == '1':
                dep = 'DEP_CENT'
            else:
                dep = 'DEP_DES'

        """
        Inicia el llamado a la funcion SQL que rellena las tablas utilizadas para consultar la poliza,
        de aucerdo a los parametos seleciconados
        """
        c = connection.cursor()
        try:
            c.execute("BEGIN")
            c.callproc("reporte_polizas",
                       [int(periodo), int(cat_anio_fiscal), dependencia, int(tipo_nomina), organismo, excluir_list])
            results = c.fetchone()
            c.execute("COMMIT")
            for r in results:
                if r == 'Finalizado':
                    print('Finalizado Con exito.')
                    bandera = True
                elif r == False:
                    print('Fallo la respuesta.')
                else:
                    print('Ocurrió un error fuera de este mundo, salvese quien pueda!!!!! :O.')
        except Exception as err:
            error = err
            print('Error: ', error)
            c.execute("ROLLBACK")
            print('Ocurrió un error..')
        finally:
            c.close()

        """Se aloja en memoria un arcivo ZIP donde se guardaran los PDF generados por Jasper"""
        in_memory = BytesIO()
        zip = ZipFile(in_memory, "a")

        """ Abrimos los archvos para iniciar la escritura en ellos"""
        outFileEncabezado = codecs.open(str(rutaP + 'ENC_' + str(dep) +'_'+ str(nomina_text.descripcion) + '.txt'),
                              'w', 'utf-8')
        outFileDetalle = codecs.open(str(rutaP + 'DET_' + str(dep) +'_'+ str(nomina_text.descripcion) + '.txt'),
                              'w', 'utf-8')
        if periodo and cat_anio_fiscal and tipo_nomina:
            datosEnc = EncabezadoPoliza.objects.all()
            datosDetalle = DetalladoEncabezadoPoliza.objects.all()

            """
            Se escribe la informacion dentro del primer archivo
            """
            for datos in datosEnc:
                contadorEncabezado=contadorEncabezado+1
                if contadorEncabezado == datosEnc.count(): # Se condiciona la cantidad de registros a escribir para
                    # omitir un salto de linia despues del ultimo registro.
                    outFileEncabezado.write(str(datos.poliza))
                else:
                    outFileEncabezado.write(str(datos.poliza)+"\r\n")
            outFileEncabezado.close()

            """ Abrimos nuevamente el archivo con los datos ya escritos, se lee la informacion y se almacena en una variable."""
            fd_e = open(rutaP + 'ENC_' + str(dep) +'_' +str(nomina_text.descripcion) + '.txt', 'rb')
            output_E = fd_e.read()
            fd_e.close()

            for datos in datosDetalle:
                contadorDetalle=contadorDetalle+1
                if contadorDetalle == int(datosDetalle.count()):
                    outFileDetalle.write(str(datos.poliza))
                else:
                    outFileDetalle.write(str(datos.poliza) + "\r\n")
            outFileDetalle.close()

            fd_d = open(rutaP + 'DET_' + str(dep) +'_' +str(nomina_text.descripcion) + '.txt', 'rb')
            output_D = fd_d.read()
            fd_d.close()

            """se aloja en memoria un archivo zip en el que se agregaran los archivos"""
            in_memory = BytesIO()
            zip = ZipFile(in_memory, "a")
            """Se escriben los dos arhivos previamente almacenados en memoria dentro del zip"""
            zip.writestr("{}.txt".format('ENC_' + str(dep)+'_' + str(nomina_text.descripcion)), output_E)
            zip.writestr("{}.txt".format('DET_' + str(dep)+'_' + str(nomina_text.descripcion)), output_D)

            """El arhivo zip creado se configura para poder ser utilizados en equipos con sistemas Windows"""
            for file in zip.filelist:
                file.create_system = 0
            zip.close()

            response = HttpResponse(mimetype="application/zip")
            response['Content-Disposition'] = 'attachment; filename="POLIZA-{}-P{}-{}.zip"'.format(dep,periodo_text.periodo,nomina_text.descripcion)
            response['Set-Cookie']= "fileDownload=true; path=/"
            in_memory.seek(0)
            response.write(in_memory.read())
            return response

        return HttpResponseRedirect(reverse_lazy('generar-reporte-poliza'))


class GenerarEmpleadosPensionesAlimenticiasView(LoginRequiredMixin, NeverCacheMixin, View):
    def get(self, request):
        periodo = self.request.GET.get('periodo')
        dependencia = self.request.GET.get('dependencia')
        dep = Cat_dependencias.objects.get(padre_id=0, id=dependencia)
        priodo = Cat_periodo.objects.get(id=int(periodo))
        auth = ("jasperadmin", "jasperadmin")
        url = "{}rest_v2/reports{}{}.xls".format(settings.RUTA_REPORTE_FACTURA,
                                                 settings.PATH_REPORTE_FACTURA,
                                                 "reportePensionesAlimenticiasEmpleados")
        params = {
            "periodo_id": periodo,
            "dependencia_id": dependencia,
        }
        print(url)
        r = requests.get(url=url, params=params, auth=auth)
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment;filename= PensionesAlimenticiasEmpleados-{}-{}.xls'.format(
            priodo.periodo, dep.clave)
        buffer = BytesIO(r.content)
        pdf = buffer.getvalue()
        response.write(pdf)
        return response



@login_required(login_url='/login')
def listar_menores(request):
    d = date.today()
    actual = str(d)
    a = actual[:4]
    m = actual[5:7]
    dias = actual[8:10]
    print(dias)
    p = CatEmpleados.objects.get(usuario_id=request.user.id)
    queryset = CatMenor.objects.all().order_by('-id')
    menor_lista = []
    headers_menor = {"Authorization": settings.TOKEN_PUC}
    for menor in queryset:
        if menor.puc_persona_id:
            param = {'puc_persona_id': menor.puc_persona_id}
            r = requests.get(settings.PUC + '/api/persona/?', params=param, headers=headers_menor)
            if r.status_code == 200:
                respuesta = r.json()
                if respuesta:
                    for x in respuesta['results']:
                        print(x['id'], x['nombre'], x['apellido_paterno'], x['apellido_materno'])
                        nombre_persona = '%s %s %s' % (
                            x['nombre'], x['apellido_paterno'], x['apellido_materno']
                        )
                        curp = (x['curp'])
                        genero = (x['genero'])
                        fecha = (x['fecha_nacimiento'])
                        print(fecha)
                        nacimiento = fecha[:4]
                        mes = fecha[5:7]
                        dia = fecha[8:10]
                        if a == nacimiento:
                            edad = (int(m) - int(mes))
                            if edad == 0 or edad == 1:
                                edad = str(str(1) + " MES")
                                if mes == m:
                                    edad = (int(dias) - int(dia))
                                    edad = str(str(edad) + " DIAS")
                            else:
                                edad = str(str(edad) + " MESES")
                        else:
                            edad = (int(a) - int(nacimiento))
                            if edad == 1:
                                edad = str(str(edad) + " AÑO")
                            else:
                                edad = str(str(edad) + " AÑOS")

                        menor_lista.append({'nombre_persona': nombre_persona,
                                            'menor': menor,
                                            'curp': curp,
                                            'genero': genero,
                                            'edad': edad})
                        queryset = menor_lista
    return render(request, 'consulta_menores.html', {'p': p, 'menor_lista': menor_lista})
