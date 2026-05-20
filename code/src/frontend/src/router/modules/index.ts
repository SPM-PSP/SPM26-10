import admin from './admin';
import student from './student';
import teacher from './teacher';

export const routes: AuthRoute.Route[] = [student, teacher, admin];
