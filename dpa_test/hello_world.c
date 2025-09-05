#include <stdio.h>
#include <unistd.h>
#include <doca_dev.h>
#include <doca_error.h>
#include <doca_sync_event.h>
#include <doca_dpa.h>
 
/**
 * A struct that includes all needed info on registered kernels and is initialized during linkage by DPACC.
 * Variable name should be the token passed to DPACC with --app-name parameter.
 */
extern struct doca_dpa_app *dpa_hello_world_app;
 
/**
 * kernel declaration that the user must declare for each kernel and DPACC is responsible to initialize.
 * Only then, user can use this variable in relevant host APIs
 */
doca_dpa_func_t hello_world_thread_kernel;
doca_dpa_func_t hello_world_thread_notify_rpc;
 
int main(int argc, char **argv)
{
	struct doca_dev *doca_dev = NULL;
	struct doca_dpa *dpa_ctx = NULL;
	struct doca_sync_event *cpu_se = NULL;
	doca_dpa_dev_sync_event_t cpu_se_handle = 0;
	struct doca_dpa_thread *dpa_thread = NULL;
	struct doca_dpa_notification_completion *notify_comp = NULL;
	doca_dpa_dev_notification_completion_t notify_comp_handle = 0;
	uint64_t retval = 0;
 
	printf("\n----> Open DOCA Device\n");
	/* Open appropriate DOCA device doca_dev */
 
	printf("\n----> Initialize DOCA DPA Context\n");
	doca_dpa_create(doca_dev, &dpa_ctx);
	doca_dpa_set_app(dpa_ctx, dpa_hello_world_app);
	doca_dpa_start(dpa_ctx);
 
	printf("\n----> Initialize DOCA Sync Event\n");
	doca_sync_event_create(&cpu_se);
	doca_sync_event_add_publisher_location_dpa(cpu_se, dpa_ctx);
	doca_sync_event_add_subscriber_location_cpu(cpu_se, doca_dev);
	doca_sync_event_start(cpu_se);
	doca_sync_event_get_dpa_handle(cpu_se, dpa_ctx, &cpu_se_handle);
 
	printf("\n----> Initialize DOCA DPA Thread\n");
	doca_dpa_thread_create(dpa_ctx, &dpa_thread);
	doca_dpa_thread_set_func_arg(dpa_thread, &hello_world_thread_kernel, cpu_se_handle);
	doca_dpa_thread_start(dpa_thread);
 
	printf("\n----> Initialize DOCA DPA Notification Completion\n");
	doca_dpa_notification_completion_create(dpa_ctx, dpa_thread, &notify_comp);
	doca_dpa_notification_completion_start(notify_comp);
	doca_dpa_notification_completion_get_dpa_handle(notify_comp, &notify_comp_handle);
 
	printf("\n----> Run DOCA DPA Thread\n");
	doca_dpa_thread_run(dpa_thread);
 
	printf("\n----> Trigger DPA RPC\n");
	doca_dpa_rpc(dpa_ctx, &hello_world_thread_notify_rpc, &retval, notify_comp_handle);
 
	printf("\n----> Waiting For hello_world_thread_kernel To Finish\n");
	doca_sync_event_wait_gt(cpu_se, 0, 0xFFFFFFFFFFFFFFFF);
 
	printf("\n----> Destroy DOCA DPA Notification Completion\n");
	doca_dpa_notification_completion_destroy(notify_comp);
 
	printf("\n----> Destroy DOCA DPA Thread\n");
	doca_dpa_thread_destroy(dpa_thread);
 
	printf("\n----> Destroy DOCA DPA event\n");
	doca_sync_event_destroy(cpu_se);
 
	printf("\n----> Destroy DOCA DPA context\n");
	doca_dpa_destroy(dpa_ctx);
 
	printf("\n----> Destroy DOCA device\n");
	doca_dev_close(doca_dev);
 
	printf("\n----> DONE!\n");
	return 0;
}
