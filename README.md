ReadMe MicroServicio Pedidos:

En este readme encontraran todo lo relacionado con el microservicio de pedidos: encontraran multiples 
funciones tales como crear,eliminar,editar,actualizar pedidos que se posee en el sistema.

Este microservicio esta hecho con Django, el cual utiliza Python, por lo cual debemos seguir los siguientes pasos para poder correr este microservicio

Crear entorno virtual: python -m venv venv

Instalar dependencias:

#En Windows: venv\Scripts\activate

pip install -r requirements.txt

Migraciones:

python manage.py migrate

Crear Superusuario (opcional para el admin de Django):

python manage.py createsuperuser
